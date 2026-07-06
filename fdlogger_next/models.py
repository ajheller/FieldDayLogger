"""Core data models for the rewrite prototype."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class QSO:
    """A Field Day contact in the rewrite prototype."""

    qso_id: str
    call: str
    qso_class: str
    section: str
    date_time: str
    frequency: int
    band: str
    mode: str
    power: int
    grid: str = ""
    opname: str = ""
    station_id: str = ""
    operator_call: str = ""
    deleted: bool = False

    @classmethod
    def create(
        cls,
        call: str,
        qso_class: str,
        section: str,
        band: str,
        mode: str,
        power: int,
        frequency: int = 0,
        grid: str = "",
        opname: str = "",
        station_id: str = "",
        operator_call: str = "",
        date_time: str = "",
        qso_id: str = "",
    ):
        """Create a normalized QSO."""
        return cls(
            qso_id=qso_id or uuid4().hex,
            call=call.upper(),
            qso_class=qso_class.upper(),
            section=section.upper(),
            date_time=date_time or utc_now(),
            frequency=int(frequency),
            band=band.upper().replace("M", ""),
            mode=mode.upper(),
            power=int(power),
            grid=grid.upper(),
            opname=opname,
            station_id=station_id,
            operator_call=operator_call.upper(),
        )

    def apply_update(self, changes: Dict[str, Any]):
        """Return a copy with changes applied."""
        clean_changes = {}
        for key, value in changes.items():
            if key in {"call", "qso_class", "section", "band", "mode", "grid"}:
                clean_changes[key] = str(value).upper()
            elif key in {"frequency", "power"}:
                clean_changes[key] = int(value)
            elif hasattr(self, key):
                clean_changes[key] = value
        return replace(self, **clean_changes)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Deserialize from a dict."""
        return cls(**data)


@dataclass(frozen=True)
class Event:
    """Append-only event for QSO changes and sync."""

    event_id: str
    event_type: str
    station_id: str
    operator_call: str
    sequence: int
    occurred_at: str
    payload: Dict[str, Any]

    @classmethod
    def create(
        cls,
        event_type: str,
        station_id: str,
        operator_call: str,
        sequence: int,
        payload: Dict[str, Any],
        event_id: str = "",
        occurred_at: str = "",
    ):
        """Create an event."""
        return cls(
            event_id=event_id or uuid4().hex,
            event_type=event_type,
            station_id=station_id,
            operator_call=operator_call.upper(),
            sequence=int(sequence),
            occurred_at=occurred_at or utc_now(),
            payload=payload,
        )
