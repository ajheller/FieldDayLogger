"""SQLite event store for the rewrite prototype."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List

from .models import Event, QSO


class EventStore:
    """Append-only SQLite event store."""

    def __init__(self, database):
        self.database = str(database)
        self.initialize()

    def initialize(self):
        """Create tables if needed."""
        with sqlite3.connect(self.database) as conn:
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
            conn.commit()

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
            conn.execute(
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
            yield Event(
                event_id=row[0],
                event_type=row[1],
                station_id=row[2],
                operator_call=row[3],
                sequence=row[4],
                occurred_at=row[5],
                payload=json.loads(row[6]),
            )

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
        """Return QSOs after event replay."""
        contacts = list(self.replay().values())
        if include_deleted:
            return contacts
        return [qso for qso in contacts if not qso.deleted]


def remove_database(database):
    """Remove a prototype database file."""
    Path(database).unlink(missing_ok=True)
