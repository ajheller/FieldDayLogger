# FieldDayLogger Rewrite Roadmap

This document is intentionally forward-looking. It describes the direction a
rewrite could take if the prototype keeps proving useful. It is not a promise to
replace the current logger quickly, and it should stay subordinate to what real
Field Day operators need under pressure.

## North Star

FieldDayLogger should be boringly reliable during the event and forgiving after
the event.

Operators should be able to keep logging when the LAN is confused, the clock is
wrong, a laptop sleeps, a radio cable is unplugged, or a station gets rebooted.
Afterward, the club should be able to audit what happened, repair mistakes, and
generate clean exports without hand-editing fragile files.

## Design Principles

- Local-first: every station can keep logging without a server.
- Append-only history: add, edit, delete, sync, and repair are recorded as
  events.
- Rebuildable state: displayed contacts and scores can be regenerated from the
  event log.
- Operator speed first: the main screen should favor keyboard flow, not
  configuration ceremony.
- Accessibility is a core workflow requirement: normal logging should not
  require a mouse or perfect visual scanning.
- Contest rules should become modular, but only after ARRL Field Day works
  end-to-end and proves the shape of the abstraction.
- Inspectable data: SQLite, JSON payloads, and plain exported files are easier
  to recover than opaque state.
- Network skepticism: multicast can discover peers, but reliable sync needs
  idempotent delivery, ACKs, retries, and reconciliation.
- Practical security: protect log integrity, recovery, and LAN trust without
  making normal QSO entry fragile. See [`threat-model.md`](threat-model.md).
- Tests before cleverness: scoring, export, replay, sync, and migration should
  be testable without launching Qt.

## Operating Modes

### Single Station

A single laptop or Raspberry Pi should work with no network and no hub. The
local SQLite database is the source of truth. Exports are generated directly
from local state.

### Club With Hub

One station can act as a hub. Stations send append-only events to the hub, the
hub stores and redistributes events, and every station can keep working through
temporary disconnects.

### Club Without Hub

Peer-to-peer sync is possible, but should be treated as a later milestone. The
same event identity and idempotent ingest rules should make it feasible once the
hub model is stable.

### Recovery Mode

The app should have explicit repair tools:

- rebuild materialized contacts
- compare replayed state against stored projections
- import old `FieldDay.db` rows as `qso.created` events
- import reviewed paper-log CSV rows with source metadata
- merge event logs from multiple stations
- export panic ADIF/Cabrillo/CSV from any surviving database

Recovery and auditability are also security features: accidental edits,
malformed imports, corrupt media, and bad LAN packets should be diagnosable
instead of mysterious.

### Accessible Operator Mode

The CLI, GUI, and any future text-user-interface should share the same event
store. A sight-impaired operator should be able to log, review, edit, delete,
score, and export without relying on color, table position, or mouse-only
controls. See [`accessibility-ux.md`](accessibility-ux.md).

### Paper Log Mode

Paper logs should be a supported offline input path for operators who prefer
paper or for stations recovering from equipment trouble. Cellphone photos plus
OCR or LLM transcription can help, but reviewed CSV should be the import
boundary. See [`paper-log-ingest.md`](paper-log-ingest.md).

### Multi-Contest Mode

The rewrite should eventually support contests beyond ARRL Field Day, such as
Winter Field Day and ARRL VHF contests. The first working slice should still be
Field Day-shaped; a contest abstraction should be extracted after scoring,
export, duplicate detection, and replay are working for one real contest.

The event store can stay contest-neutral by storing a contest id and flexible
exchange payloads:

```text
contest_id = arrl_field_day
exchange = {"class": "2A", "section": "SCV"}

contest_id = arrl_vhf
exchange = {"grid": "CM87"}
```

## Roadmap

### Phase 0: Current Prototype

Already present on `rewrite-prototype`:

- QSO and event dataclasses.
- SQLite append-only event log.
- Materialized `contacts` table.
- Event replay and projection rebuild.
- Create, edit, delete, duplicate lookup, and scoring.
- Minimal PyQt5 logger shell.
- Console-script CLI for add, edit, delete, list, score, rebuild, and other
  non-GUI workflows.
- Store-only soak harness.
- Makefile shortcuts for install, checks, GUI launch, and soak runs.

Exit criteria:

- `make check` is green.
- `make smoke-soak` is green.
- `make install-dev` exposes `fdlogger-next`, `fdlogger-next-cli`, and
  `fdlogger-next-soak`.

### Phase 1: Operator-Speed Local Logger

Make the prototype feel like something an operator could actually use for a
small practice session.

Work:

- keyboard-first logging flow
- screen-reader and keyboard-only smoke testing
- sticky band, mode, power, class, and section defaults
- Enter logs, Esc clears, predictable tab order
- preference file for station ID, operator call, class, section, and DB path
- better selected-QSO edit/delete workflow
- clearer duplicate warning
- basic CSV export for quick inspection
- documented accessible practice workflow
- printable paper-log sheet draft

Exit criteria:

- 30 minute manual practice session without touching the mouse for normal QSOs.
- A terminal/screen-reader workflow can add, list, score, rebuild, edit, and
  delete practice contacts.
- All user-visible QSO changes are represented as events.
- Rebuild from events produces the same displayed log and score.

### Phase 2: Storage and Export Confidence

Make the new data model trustworthy before networking complicates it.

Work:

- ADIF export from the new model
- Cabrillo export from the new model
- golden-file tests for exports
- import current `FieldDay.db` rows as events
- import reviewed paper-log CSV rows with sheet/row/source-image metadata
- migration tests with representative old databases
- better integrity diagnostics in the CLI

Exit criteria:

- Existing known-good logs export identically or with reviewed, documented
  differences.
- Imported current-format databases can be rebuilt and exported.
- Paper-imported QSOs can be traced back to sheet id, row number, and source
  image.
- CLI repair and export commands work without Qt.

### Phase 3: Long-Run Local Soak

Use synthetic tests to find boring failures early.

Work:

- 12 hour MacBook soak at high event rate
- 36 hour target-laptop or Raspberry Pi soak at realistic rate
- GUI/event-loop soak harness
- memory and latency trend review from JSONL output
- repeated rebuild/reopen cycles

Exit criteria:

- No replay/materialized mismatches.
- No unbounded memory growth under expected load.
- Operation latency stays comfortably below operator-visible thresholds.
- Databases survive restarts and rebuilds.

### Phase 4: Reliable Hub Sync

Build networking around the event log instead of around mutable rows.

Work:

- durable outbound queue
- event ingest by UUID
- ACK tracking
- retry with backoff
- reconnect and reconcile
- hub diagnostics
- packet loss/reorder simulator

Exit criteria:

- Two or more stations can log while one station disconnects and later
  reconciles.
- Duplicate event delivery is harmless.
- Hub restart does not lose committed station events.
- A merged event log rebuilds to the expected contact set.

### Phase 5: Field Day Feature Parity

Bring over the integrations that make the current logger useful in practice.

Work:

- CAT/flrig/rigctld polling
- CW macros
- N1MM packets
- WSJT-X UDP ingest
- Super Check Partial and section assist
- Cloudlog and callsign lookup integrations
- station and network diagnostics panel

Exit criteria:

- Existing workflows have a known replacement or a deliberate non-goal.
- Operators can run a full mock event using the rewrite app.
- Exports are submission-ready.

### Phase 6: Contest Rule Modules

Extract contest-specific behavior once the Field Day workflow is proven.

Work:

- define a small `ContestRules` interface
- move ARRL Field Day exchange validation, duplicate keys, scoring, export
  fields, time-window handling, and bonus categories into a rule module
- keep the core event store independent of any one exchange shape
- add Winter Field Day as the second contest, because it is culturally close to
  Field Day but different enough to test the abstraction
- add ARRL VHF later, because grids, rovers, band rules, and scoring are
  different enough to expose weak assumptions
- keep contest modules testable without Qt

Possible package shape:

```text
fdlogger_core/
  contests/
    arrl_field_day.py
    winter_field_day.py
    arrl_vhf.py
```

Each contest module should own:

- exchange fields and validation
- duplicate key rules
- band and mode rules
- scoring rules
- export format requirements
- contest time-window rules
- bonus categories, when supported

Exit criteria:

- ARRL Field Day behavior is unchanged after extraction.
- Winter Field Day can log, score, detect duplicates, and export a practice
  file using the same core storage model.
- VHF contest support can be prototyped without contorting Field Day fields.
- Contest-specific code does not leak back into the event store.

### Phase 7: Deployment and Packaging

Make it installable and understandable for a club, not just for the developer.

Work:

- documented install path for macOS, Linux, Raspberry Pi OS, and Windows
- sample club setup guide
- backup and recovery guide
- release checklist
- versioned database migrations
- crash/diagnostic bundle command

Exit criteria:

- A clean machine can be set up from docs.
- A club can run a practice session using only released artifacts.
- Recovery instructions are tested, not merely written.
- Accessible station setup instructions are tested with real assistive tooling.

## What Not To Do Yet

- Do not optimize sync before storage and replay are boring.
- Do not polish the GUI before keyboard flow works.
- Do not port every integration before export correctness is proven.
- Do not remove the existing app while the rewrite is still experimental.
- Do not make the hub mandatory for normal single-station logging.
- Do not generalize contest rules before Field Day scoring and exports are
  proven.

## Open Questions

- Should the long-term GUI stay PyQt5, move to PySide6, or track the current
  app's dependency choices for easier adoption?
- Should the hub be built into the app, run as a separate command, or both?
- What is the minimum export set needed before a club practice test?
- How much old-database migration is required for real users?
- How should clock skew be displayed and repaired without slowing operators?
- Should the alternate operator UX be a richer CLI, a TUI, a speech-first mode,
  or a combination?
- What is the smallest contest-rule interface that supports Field Day, Winter
  Field Day, and VHF contests without forcing all contests into the same
  exchange shape?

## Suggested Next Slice

The next high-value slice is Phase 1: operator-speed local logging. That means
sticky defaults, preference persistence, keyboard behavior, and a cleaner edit
flow. Once that feels natural, the soak harness can test the storage layer while
humans test whether the logger actually feels good under Field Day pressure.
