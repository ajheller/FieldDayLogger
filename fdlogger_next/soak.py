"""Synthetic soak test for the rewrite prototype."""

import argparse
import json
import random
import sqlite3
import time
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path

from .models import QSO, utc_now
from .scoring import calculate_score
from .store import EventStore


CALL_PREFIXES = ("K6", "N6", "W6", "AK6", "KM6", "KK6", "W1", "N0", "VE7")
CALL_SUFFIXES = (
    "ABC",
    "XYZ",
    "FD",
    "HAM",
    "QSO",
    "LOG",
    "SVC",
    "OTA",
    "CW",
    "DIG",
)
SECTIONS = ("SCV", "SV", "EB", "SF", "SJV", "LAX", "ORG", "SDG", "CT", "WWA")
CLASSES = ("1A", "2A", "3A", "4A", "1D", "1E", "2F")
BANDS = ("160", "80", "40", "20", "15", "10", "6", "2")
MODES = ("CW", "PH", "DG")


class IntegrityError(RuntimeError):
    """Raised when materialized state diverges from replayed event state."""


@dataclass
class SoakConfig:
    """Configuration for a store-only synthetic soak test."""

    database: str
    seconds: float
    rate: float
    log: str = ""
    seed: int = 0
    station: str = "soak-1"
    operator: str = "SOAK"
    check_interval: float = 60.0
    rebuild_interval: float = 300.0
    restart_interval: float = 7200.0
    max_operations: int = 0
    create_percent: int = 85
    edit_percent: int = 10
    delete_percent: int = 5
    progress: bool = True


@dataclass
class SoakSample:
    """One JSONL sample from a soak run."""

    timestamp: str
    elapsed_seconds: float
    operations: int
    events: int
    active_qsos: int
    total_qsos: int
    score: int
    base_score: int
    creates: int
    edits: int
    deletes: int
    rebuilds: int
    restarts: int
    checks: int
    avg_latency_ms: float
    max_latency_ms: float
    rss_kb: int


class SoakRunner:
    """Run synthetic create/edit/delete traffic against an EventStore."""

    def __init__(self, config: SoakConfig):
        self.config = config
        self.random = random.Random(config.seed)
        self.store = EventStore(config.database)
        self.active_ids = [qso.qso_id for qso in self.store.list_qsos()]
        self.creates = 0
        self.edits = 0
        self.deletes = 0
        self.rebuilds = 0
        self.restarts = 0
        self.checks = 0
        self.latencies = []
        self.max_latency = 0.0

    def run(self):
        """Run until the configured duration or operation limit is reached."""
        start = time.monotonic()
        deadline = start + self.config.seconds
        next_check = start + self.config.check_interval
        next_rebuild = start + self.config.rebuild_interval
        next_restart = start + self.config.restart_interval
        operations = 0
        log_file = self._open_log()

        try:
            while time.monotonic() < deadline:
                if self.config.max_operations and operations >= self.config.max_operations:
                    break

                operation_start = time.monotonic()
                self.run_operation()
                elapsed_operation = time.monotonic() - operation_start
                self.latencies.append(elapsed_operation)
                self.max_latency = max(self.max_latency, elapsed_operation)
                operations += 1

                now = time.monotonic()
                if now >= next_rebuild:
                    self.store.rebuild_contacts()
                    self.rebuilds += 1
                    self.refresh_active_ids()
                    next_rebuild = now + self.config.rebuild_interval
                if now >= next_restart:
                    self.store = EventStore(self.config.database)
                    self.restarts += 1
                    self.refresh_active_ids()
                    next_restart = now + self.config.restart_interval
                if now >= next_check:
                    self.assert_integrity()
                    self.checks += 1
                    sample = self.sample(start, operations)
                    self.write_sample(log_file, sample)
                    next_check = now + self.config.check_interval

                self.sleep_for_rate(operation_start)

            self.assert_integrity()
            self.checks += 1
            sample = self.sample(start, operations)
            self.write_sample(log_file, sample)
            return sample
        finally:
            if log_file:
                log_file.close()

    def run_operation(self):
        """Run one weighted synthetic operation."""
        action = self.choose_action()
        if action == "edit":
            self.edit_random_qso()
        elif action == "delete":
            self.delete_random_qso()
        else:
            self.create_random_qso()

    def choose_action(self):
        """Choose create, edit, or delete with configured weights."""
        if not self.active_ids:
            return "create"
        roll = self.random.randint(1, 100)
        if roll <= self.config.create_percent:
            return "create"
        if roll <= self.config.create_percent + self.config.edit_percent:
            return "edit"
        return "delete"

    def create_random_qso(self):
        """Create one synthetic QSO."""
        band = self.random.choice(BANDS)
        qso = QSO.create(
            call=self.random_call(),
            qso_class=self.random.choice(CLASSES),
            section=self.random.choice(SECTIONS),
            band=band,
            mode=self.random.choice(MODES),
            power=self.random.choice((5, 10, 50, 100)),
            frequency=self.random_frequency(band),
            station_id=self.config.station,
            operator_call=self.config.operator,
        )
        self.store.create_qso(qso)
        self.active_ids.append(qso.qso_id)
        self.creates += 1

    def edit_random_qso(self):
        """Edit one active synthetic QSO."""
        qso = self.random_active_qso()
        if not qso:
            self.create_random_qso()
            return
        changes = {
            "section": self.random.choice(SECTIONS),
            "qso_class": self.random.choice(CLASSES),
            "power": self.random.choice((5, 10, 50, 100)),
        }
        self.store.update_qso(qso.qso_id, changes, qso.station_id, self.config.operator)
        self.edits += 1

    def delete_random_qso(self):
        """Soft-delete one active synthetic QSO."""
        qso = self.random_active_qso()
        if not qso:
            self.create_random_qso()
            return
        self.store.delete_qso(qso.qso_id, qso.station_id, self.config.operator)
        try:
            self.active_ids.remove(qso.qso_id)
        except ValueError:
            self.refresh_active_ids()
        self.deletes += 1

    def random_active_qso(self):
        """Return a random active QSO, refreshing once for stale IDs."""
        if not self.active_ids:
            return None
        qso_id = self.random.choice(self.active_ids)
        qso = self.store.get_qso(qso_id)
        if qso:
            return qso
        self.refresh_active_ids()
        if not self.active_ids:
            return None
        return self.store.get_qso(self.random.choice(self.active_ids))

    def random_call(self):
        """Return a synthetic call sign with occasional intentional repeats."""
        prefix = self.random.choice(CALL_PREFIXES)
        suffix = self.random.choice(CALL_SUFFIXES)
        number = self.random.randint(0, 9999)
        return f"{prefix}{suffix}{number:04d}"

    def random_frequency(self, band):
        """Return an approximate frequency in Hz."""
        bases = {
            "160": 1810000,
            "80": 3550000,
            "40": 7040000,
            "20": 14040000,
            "15": 21040000,
            "10": 28040000,
            "6": 50125000,
            "2": 146520000,
        }
        return bases[band] + self.random.randint(0, 50000)

    def refresh_active_ids(self):
        """Refresh active IDs from the materialized contact table."""
        self.active_ids = [qso.qso_id for qso in self.store.list_qsos()]

    def assert_integrity(self):
        """Compare materialized contacts to a full event replay."""
        materialized = {
            qso.qso_id: qso.to_dict()
            for qso in self.store.list_qsos(include_deleted=True)
        }
        replayed = {
            qso_id: qso.to_dict()
            for qso_id, qso in self.store.replay().items()
        }
        if materialized != replayed:
            raise IntegrityError("materialized contacts do not match replayed events")

    def sample(self, start, operations):
        """Build one status sample."""
        qsos = self.store.list_qsos()
        total_qsos = len(self.store.list_qsos(include_deleted=True))
        score, base_score = calculate_score(qsos)
        return SoakSample(
            timestamp=utc_now(),
            elapsed_seconds=round(time.monotonic() - start, 3),
            operations=operations,
            events=self.count_events(),
            active_qsos=len(qsos),
            total_qsos=total_qsos,
            score=score,
            base_score=base_score,
            creates=self.creates,
            edits=self.edits,
            deletes=self.deletes,
            rebuilds=self.rebuilds,
            restarts=self.restarts,
            checks=self.checks,
            avg_latency_ms=round(self.average_latency() * 1000, 3),
            max_latency_ms=round(self.max_latency * 1000, 3),
            rss_kb=current_rss_kb(),
        )

    def count_events(self):
        """Return the current number of events."""
        with closing(sqlite3.connect(self.config.database)) as conn:
            row = conn.execute("select count(*) from events").fetchone()
        return int(row[0])

    def average_latency(self):
        """Return the average operation latency in seconds."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    def sleep_for_rate(self, operation_start):
        """Throttle to the configured operation rate."""
        if self.config.rate <= 0:
            return
        interval = 60.0 / self.config.rate
        remaining = interval - (time.monotonic() - operation_start)
        if remaining > 0:
            time.sleep(remaining)

    def _open_log(self):
        if not self.config.log:
            return None
        path = Path(self.config.log)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.open("a", encoding="utf-8")

    def write_sample(self, log_file, sample):
        """Write and optionally print a JSONL sample."""
        line = json.dumps(asdict(sample), sort_keys=True)
        if log_file:
            log_file.write(line + "\n")
            log_file.flush()
        if self.config.progress:
            print(line, flush=True)


def current_rss_kb():
    """Return max RSS in KiB when the platform exposes it."""
    try:
        import resource
    except ImportError:
        return 0
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = int(usage.ru_maxrss)
    if rss > 0 and sys_platform_is_macos():
        return rss // 1024
    return rss


def sys_platform_is_macos():
    """Return True on macOS without importing platform in the hot path."""
    import sys

    return sys.platform == "darwin"


def build_parser():
    """Build the soak command parser."""
    parser = argparse.ArgumentParser(prog="fdlogger-next-soak")
    parser.add_argument("database", help="prototype SQLite database")
    parser.add_argument("--hours", type=float, default=36.0)
    parser.add_argument("--seconds", type=float, default=0.0)
    parser.add_argument("--rate", type=float, default=30.0, help="operations per minute")
    parser.add_argument("--log", default="", help="JSONL output path")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--station", default="soak-1")
    parser.add_argument("--operator", default="SOAK")
    parser.add_argument("--check-interval", type=float, default=60.0)
    parser.add_argument("--rebuild-interval", type=float, default=300.0)
    parser.add_argument("--restart-interval", type=float, default=7200.0)
    parser.add_argument("--max-operations", type=int, default=0)
    parser.add_argument("--create-percent", type=int, default=85)
    parser.add_argument("--edit-percent", type=int, default=10)
    parser.add_argument("--delete-percent", type=int, default=5)
    parser.add_argument("--quiet", action="store_true")
    return parser


def config_from_args(args):
    """Create SoakConfig from argparse results."""
    seconds = args.seconds if args.seconds > 0 else args.hours * 60 * 60
    return SoakConfig(
        database=args.database,
        seconds=seconds,
        rate=args.rate,
        log=args.log,
        seed=args.seed,
        station=args.station,
        operator=args.operator,
        check_interval=args.check_interval,
        rebuild_interval=args.rebuild_interval,
        restart_interval=args.restart_interval,
        max_operations=args.max_operations,
        create_percent=args.create_percent,
        edit_percent=args.edit_percent,
        delete_percent=args.delete_percent,
        progress=not args.quiet,
    )


def run(argv=None):
    """Run the store-only soak test."""
    args = build_parser().parse_args(argv)
    sample = SoakRunner(config_from_args(args)).run()
    return 0 if sample else 1


if __name__ == "__main__":
    raise SystemExit(run())
