"""SQLite event store for the rewrite prototype."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List

from .models import Event, QSO

SCHEMA_VERSION = 1

CONTACT_COLUMNS = (
    "qso_id",
    "call",
    "qso_class",
    "section",
    "date_time",
    "frequency",
    "band",
    "mode",
    "power",
    "grid",
    "opname",
    "station_id",
    "operator_call",
    "deleted",
    "updated_event_id",
)
CONTACT_SELECT = ", ".join(CONTACT_COLUMNS)


class EventStore:
    """Append-only SQLite event store."""

    def __init__(self, database):
        self.database = str(database)
        self.initialize()

    def initialize(self):
        """Create tables if needed."""
        needs_rebuild = False
        with sqlite3.connect(self.database) as conn:
            current_version = conn.execute("pragma user_version").fetchone()[0]
            conn.execute(
                """
                create table if not exists events (
                    id integer primary key,
                    event_id text not null unique,
                    event_type text not null,
                    station_id text not null,
                    operator_call text not null,
                    sequence integer not null,
                    occurred_at text not null,
                    payload text not null,
                    sync_status text not null default 'local'
                )
                """
            )
            conn.execute(
                """
                create index if not exists idx_events_sequence
                on events(station_id, sequence)
                """
            )
            conn.execute(
                """
                create table if not exists contacts (
                    qso_id text primary key,
                    call text not null,
                    qso_class text not null,
                    section text not null,
                    date_time text not null,
                    frequency integer not null,
                    band text not null,
                    mode text not null,
                    power integer not null,
                    grid text not null default '',
                    opname text not null default '',
                    station_id text not null default '',
                    operator_call text not null default '',
                    deleted integer not null default 0,
                    updated_event_id text not null
                )
                """
            )
            conn.execute(
                """
                create index if not exists idx_contacts_active
                on contacts(deleted, call, band, mode)
                """
            )
            if current_version < SCHEMA_VERSION:
                needs_rebuild = True
                conn.execute(f"pragma user_version = {SCHEMA_VERSION}")
            conn.commit()
        if needs_rebuild:
            self.rebuild_contacts()

    def next_sequence(self, station_id):
        """Return the next local sequence number for a station."""
        with sqlite3.connect(self.database) as conn:
            row = conn.execute(
                "select coalesce(max(sequence), 0) + 1 from events where station_id = ?",
                (station_id,),
            ).fetchone()
            return int(row[0])

    def append(self, event: Event):
        """Append an event if it has not already been stored."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.execute(
                """
                insert or ignore into events (
                    event_id, event_type, station_id, operator_call, sequence,
                    occurred_at, payload
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.station_id,
                    event.operator_call,
                    event.sequence,
                    event.occurred_at,
                    json.dumps(event.payload, sort_keys=True),
                ),
            )
            if cursor.rowcount:
                self._apply_event(conn, event)
            conn.commit()
        return event

    def create_qso(self, qso: QSO):
        """Append a QSO creation event."""
        return self.append(
            Event.create(
                event_type="qso.created",
                station_id=qso.station_id,
                operator_call=qso.operator_call,
                sequence=self.next_sequence(qso.station_id),
                payload=qso.to_dict(),
            )
        )

    def update_qso(self, qso_id, changes, station_id, operator_call):
        """Append a QSO update event."""
        payload = {"qso_id": qso_id, "changes": changes}
        return self.append(
            Event.create(
                event_type="qso.updated",
                station_id=station_id,
                operator_call=operator_call,
                sequence=self.next_sequence(station_id),
                payload=payload,
            )
        )

    def delete_qso(self, qso_id, station_id, operator_call):
        """Append a QSO delete event."""
        return self.append(
            Event.create(
                event_type="qso.deleted",
                station_id=station_id,
                operator_call=operator_call,
                sequence=self.next_sequence(station_id),
                payload={"qso_id": qso_id},
            )
        )

    def events(self) -> Iterable[Event]:
        """Yield events in replay order."""
        with sqlite3.connect(self.database) as conn:
            rows = conn.execute(
                """
                select event_id, event_type, station_id, operator_call, sequence,
                       occurred_at, payload
                from events
                order by id
                """
            ).fetchall()
        for row in rows:
            yield self._event_from_row(row)

    def replay(self) -> Dict[str, QSO]:
        """Replay the event stream into QSO state."""
        contacts: Dict[str, QSO] = {}
        for event in self.events():
            if event.event_type == "qso.created":
                qso = QSO.from_dict(event.payload)
                contacts[qso.qso_id] = qso
            elif event.event_type == "qso.updated":
                qso = contacts.get(event.payload["qso_id"])
                if qso:
                    contacts[qso.qso_id] = qso.apply_update(event.payload["changes"])
            elif event.event_type == "qso.deleted":
                qso = contacts.get(event.payload["qso_id"])
                if qso:
                    contacts[qso.qso_id] = qso.apply_update({"deleted": True})
        return contacts

    def list_qsos(self, include_deleted=False) -> List[QSO]:
        """Return QSOs from the materialized contact table."""
        where = "" if include_deleted else "where deleted = 0"
        with sqlite3.connect(self.database) as conn:
            rows = conn.execute(
                f"""
                select {CONTACT_SELECT}
                from contacts
                {where}
                order by date_time, qso_id
                """
            ).fetchall()
        return [self._qso_from_contact_row(row) for row in rows]

    def get_qso(self, qso_id, include_deleted=False):
        """Return one QSO from the materialized contact table."""
        deleted_filter = "" if include_deleted else "and deleted = 0"
        with sqlite3.connect(self.database) as conn:
            row = conn.execute(
                f"""
                select {CONTACT_SELECT}
                from contacts
                where qso_id = ?
                {deleted_filter}
                """,
                (qso_id,),
            ).fetchone()
        if row is None:
            return None
        return self._qso_from_contact_row(row)

    def find_duplicates(self, call, band, mode, exclude_qso_id="") -> List[QSO]:
        """Return active QSOs that match the Field Day duplicate key."""
        call = str(call).strip().upper()
        band = str(band).strip().upper().replace("M", "")
        mode = str(mode).strip().upper()
        with sqlite3.connect(self.database) as conn:
            rows = conn.execute(
                f"""
                select {CONTACT_SELECT}
                from contacts
                where deleted = 0
                  and call = ?
                  and band = ?
                  and mode = ?
                  and qso_id != ?
                order by date_time, qso_id
                """,
                (call, band, mode, exclude_qso_id),
            ).fetchall()
        return [self._qso_from_contact_row(row) for row in rows]

    def rebuild_contacts(self):
        """Rebuild the materialized contact table from the event log."""
        with sqlite3.connect(self.database) as conn:
            conn.execute("delete from contacts")
            rows = conn.execute(
                """
                select event_id, event_type, station_id, operator_call, sequence,
                       occurred_at, payload
                from events
                order by id
                """
            ).fetchall()
            for row in rows:
                self._apply_event(conn, self._event_from_row(row))
            conn.commit()
        return len(rows)

    @staticmethod
    def _event_from_row(row):
        return Event(
            event_id=row[0],
            event_type=row[1],
            station_id=row[2],
            operator_call=row[3],
            sequence=row[4],
            occurred_at=row[5],
            payload=json.loads(row[6]),
        )

    @staticmethod
    def _qso_from_contact_row(row):
        return QSO(
            qso_id=row[0],
            call=row[1],
            qso_class=row[2],
            section=row[3],
            date_time=row[4],
            frequency=row[5],
            band=row[6],
            mode=row[7],
            power=row[8],
            grid=row[9],
            opname=row[10],
            station_id=row[11],
            operator_call=row[12],
            deleted=bool(row[13]),
        )

    @classmethod
    def _write_contact(cls, conn, qso: QSO, event_id):
        conn.execute(
            f"""
            insert or replace into contacts ({CONTACT_SELECT})
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                qso.qso_id,
                qso.call,
                qso.qso_class,
                qso.section,
                qso.date_time,
                qso.frequency,
                qso.band,
                qso.mode,
                qso.power,
                qso.grid,
                qso.opname,
                qso.station_id,
                qso.operator_call,
                1 if qso.deleted else 0,
                event_id,
            ),
        )

    @classmethod
    def _load_contact(cls, conn, qso_id):
        row = conn.execute(
            f"""
            select {CONTACT_SELECT}
            from contacts
            where qso_id = ?
            """,
            (qso_id,),
        ).fetchone()
        if row is None:
            return None
        return cls._qso_from_contact_row(row)

    @classmethod
    def _apply_event(cls, conn, event: Event):
        if event.event_type == "qso.created":
            cls._write_contact(conn, QSO.from_dict(event.payload), event.event_id)
        elif event.event_type == "qso.updated":
            qso = cls._load_contact(conn, event.payload["qso_id"])
            if qso:
                cls._write_contact(
                    conn,
                    qso.apply_update(event.payload.get("changes", {})),
                    event.event_id,
                )
        elif event.event_type == "qso.deleted":
            qso = cls._load_contact(conn, event.payload["qso_id"])
            if qso:
                cls._write_contact(
                    conn,
                    qso.apply_update({"deleted": True}),
                    event.event_id,
                )


def remove_database(database):
    """Remove a prototype database file."""
    Path(database).unlink(missing_ok=True)
