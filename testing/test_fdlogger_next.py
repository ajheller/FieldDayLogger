"""Tests for the rewrite prototype."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fdlogger_next.models import QSO
from fdlogger_next.scoring import calculate_score
from fdlogger_next.store import EventStore


class EventStoreTest(unittest.TestCase):
    """Event store behavior."""

    def test_create_update_delete_replay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EventStore(Path(tmpdir) / "next.db")
            qso = QSO.create(
                call="k6abc",
                qso_class="1a",
                section="scv",
                band="20m",
                mode="cw",
                power=100,
                station_id="station-1",
                operator_call="ak6im",
            )

            store.create_qso(qso)
            store.update_qso(
                qso.qso_id,
                {"qso_class": "2a", "section": "sv", "operator_call": "n6xyz"},
                station_id="station-1",
                operator_call="ak6im",
            )

            [updated] = store.list_qsos()
            self.assertEqual(updated.call, "K6ABC")
            self.assertEqual(updated.qso_class, "2A")
            self.assertEqual(updated.section, "SV")
            self.assertEqual(updated.operator_call, "N6XYZ")

            store.delete_qso(qso.qso_id, station_id="station-1", operator_call="ak6im")
            self.assertEqual(store.list_qsos(), [])
            [deleted] = store.list_qsos(include_deleted=True)
            self.assertTrue(deleted.deleted)

    def test_rebuild_contacts_from_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EventStore(Path(tmpdir) / "next.db")
            qso = QSO.create("K6ABC", "1A", "SCV", "20", "CW", 100)

            store.create_qso(qso)
            store.update_qso(qso.qso_id, {"section": "SV"}, "", "")

            with sqlite3.connect(store.database) as conn:
                conn.execute("delete from contacts")
                conn.commit()

            self.assertEqual(store.list_qsos(include_deleted=True), [])
            self.assertEqual(store.rebuild_contacts(), 2)
            [rebuilt] = store.list_qsos(include_deleted=True)
            self.assertEqual(rebuilt.section, "SV")

    def test_duplicate_event_does_not_update_contacts_twice(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EventStore(Path(tmpdir) / "next.db")
            qso = QSO.create("K6ABC", "1A", "SCV", "20", "CW", 100)

            event = store.create_qso(qso)
            store.append(event)

            self.assertEqual(len(list(store.events())), 1)
            self.assertEqual(len(store.list_qsos(include_deleted=True)), 1)

    def test_get_qso_and_find_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EventStore(Path(tmpdir) / "next.db")
            qso = QSO.create("k6abc", "1a", "scv", "20m", "cw", 100)
            other_band = QSO.create("K6ABC", "1A", "SCV", "40", "CW", 100)

            store.create_qso(qso)
            store.create_qso(other_band)

            self.assertEqual(store.get_qso(qso.qso_id).call, "K6ABC")
            duplicates = store.find_duplicates("k6abc", "20m", "cw")
            self.assertEqual([duplicate.qso_id for duplicate in duplicates], [qso.qso_id])
            self.assertEqual(store.find_duplicates("K6ABC", "20", "CW", qso.qso_id), [])
            self.assertEqual(store.find_duplicates("K6ABC", "15", "CW"), [])

            store.delete_qso(qso.qso_id, "", "")
            self.assertIsNone(store.get_qso(qso.qso_id))
            self.assertEqual(store.get_qso(qso.qso_id, include_deleted=True).call, "K6ABC")
            self.assertEqual(store.find_duplicates("K6ABC", "20", "CW"), [])

    def test_sequence_is_per_station(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EventStore(Path(tmpdir) / "next.db")
            first = QSO.create("K6ABC", "1A", "SCV", "20", "CW", 100, station_id="a")
            second = QSO.create("W1AW", "2A", "CT", "40", "PH", 100, station_id="b")

            store.create_qso(first)
            store.create_qso(second)

            sequences = [(event.station_id, event.sequence) for event in store.events()]
            self.assertEqual(sequences, [("a", 1), ("b", 1)])


class ScoringTest(unittest.TestCase):
    """Scoring behavior."""

    def test_calculates_base_and_total_score(self):
        qsos = [
            QSO.create("K6ABC", "1A", "SCV", "20", "CW", 100),
            QSO.create("W1AW", "2A", "CT", "40", "PH", 100),
            QSO.create("N6XYZ", "3A", "SV", "15", "DI", 100),
        ]

        self.assertEqual(calculate_score(qsos), (10, 5))
        self.assertEqual(calculate_score(qsos, qrp=True, alt_power=True), (25, 5))


if __name__ == "__main__":
    unittest.main()
