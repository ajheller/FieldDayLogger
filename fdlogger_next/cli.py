"""Tiny CLI for the rewrite prototype."""

import argparse

from .models import QSO
from .scoring import calculate_score
from .store import EventStore


def build_parser():
    """Build the command parser."""
    parser = argparse.ArgumentParser(prog="fdlogger-next-cli")
    parser.add_argument("database", help="prototype SQLite database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="initialize the prototype database")

    sample_parser = subparsers.add_parser("sample", help="add a sample QSO")
    sample_parser.add_argument("--station", default="station-1")
    sample_parser.add_argument("--operator", default="AK6IM")

    add_parser = subparsers.add_parser("add", help="add a QSO")
    add_parser.add_argument("--call", required=True)
    add_parser.add_argument("--class-name", dest="qso_class", required=True)
    add_parser.add_argument("--section", required=True)
    add_parser.add_argument("--band", required=True)
    add_parser.add_argument("--mode", required=True)
    add_parser.add_argument("--power", type=int, required=True)
    add_parser.add_argument("--frequency", type=int, default=0)
    add_parser.add_argument("--station", default="station-1")
    add_parser.add_argument("--operator", default="")

    edit_parser = subparsers.add_parser("edit", help="edit an active QSO")
    edit_parser.add_argument("qso_id")
    edit_parser.add_argument("--call")
    edit_parser.add_argument("--class-name", dest="qso_class")
    edit_parser.add_argument("--section")
    edit_parser.add_argument("--band")
    edit_parser.add_argument("--mode")
    edit_parser.add_argument("--power", type=int)
    edit_parser.add_argument("--frequency", type=int)
    edit_parser.add_argument("--station", default="")
    edit_parser.add_argument("--operator", default="")

    delete_parser = subparsers.add_parser("delete", help="delete an active QSO")
    delete_parser.add_argument("qso_id")
    delete_parser.add_argument("--station", default="")
    delete_parser.add_argument("--operator", default="")

    subparsers.add_parser("list", help="list active QSOs")
    subparsers.add_parser("rebuild", help="rebuild materialized contacts")
    subparsers.add_parser("score", help="show current score")
    return parser


def run(argv=None):
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    store = EventStore(args.database)

    if args.command == "init":
        print(f"initialized {args.database}")
        return 0

    if args.command == "sample":
        qso = QSO.create(
            call="K6ABC",
            qso_class="1A",
            section="SCV",
            band="20",
            mode="CW",
            power=100,
            frequency=14030000,
            station_id=args.station,
            operator_call=args.operator,
        )
        store.create_qso(qso)
        print(qso.qso_id)
        return 0

    if args.command == "add":
        qso = QSO.create(
            call=args.call,
            qso_class=args.qso_class,
            section=args.section,
            band=args.band,
            mode=args.mode,
            power=args.power,
            frequency=args.frequency,
            station_id=args.station,
            operator_call=args.operator,
        )
        store.create_qso(qso)
        print(qso.qso_id)
        return 0

    if args.command == "edit":
        qso = store.get_qso(args.qso_id)
        if not qso:
            print(f"qso not found: {args.qso_id}")
            return 1
        changes = {}
        for key in (
            "call",
            "qso_class",
            "section",
            "band",
            "mode",
            "power",
            "frequency",
        ):
            value = getattr(args, key)
            if value is not None:
                changes[key] = value
        if not changes:
            print("no changes requested")
            return 1
        store.update_qso(
            args.qso_id,
            changes,
            station_id=args.station or qso.station_id,
            operator_call=args.operator or qso.operator_call,
        )
        updated = store.get_qso(args.qso_id)
        print(
            f"{updated.qso_id} {updated.call} {updated.qso_class} "
            f"{updated.section} {updated.band}M {updated.mode} {updated.power}W"
        )
        return 0

    if args.command == "delete":
        qso = store.get_qso(args.qso_id)
        if not qso:
            print(f"qso not found: {args.qso_id}")
            return 1
        store.delete_qso(
            args.qso_id,
            station_id=args.station or qso.station_id,
            operator_call=args.operator or qso.operator_call,
        )
        print(f"deleted {qso.qso_id} {qso.call}")
        return 0

    if args.command == "list":
        for qso in store.list_qsos():
            print(
                f"{qso.qso_id} {qso.call} {qso.qso_class} {qso.section} "
                f"{qso.band}M {qso.mode} {qso.power}W"
            )
        return 0

    if args.command == "rebuild":
        count = store.rebuild_contacts()
        print(f"rebuilt contacts from {count} events")
        return 0

    if args.command == "score":
        total, base = calculate_score(store.list_qsos())
        print(f"score={total} base={base}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
