# FieldDayLogger Rewrite Architecture Sketch

This branch is an experimental design space for a possible rewrite. The goal is
not to replace the current application quickly, but to outline a safer shape for
a Field Day logger that can survive tired operators, bad LANs, clock drift,
unplugged cables, and post-event cleanup.

## Goals

- Keep local logging fast and reliable even when the network is broken.
- Make every QSO add, edit, and delete recoverable and auditable.
- Make scoring, duplicate detection, and exports testable without a GUI.
- Support Linux and Raspberry Pi class machines as first-class targets.
- Preserve practical Field Day workflows: keyboard-first logging, CW macros,
  CAT, WSJT-X, N1MM packets, Cloudlog, and offline operation.
- Prefer boring, inspectable local files over required cloud services.

## Non-Goals

- Do not require internet access during the event.
- Do not require a central server for a single-station setup.
- Do not make the GUI the source of truth for contest logic.
- Do not rewrite everything before proving the sync and storage model.

## Proposed Packages

```text
fdlogger_core
  Contest rules, exchanges, sections, scoring, duplicate checks, ADIF/Cabrillo.

fdlogger_store
  SQLite schema, migrations, event log, materialized QSO view, sync state.

fdlogger_sync
  LAN discovery, station identity, durable message exchange, retry/reconcile.

fdlogger_integrations
  CAT, WSJT-X UDP, N1MM UDP, Cloudlog, QRZ/HamDB/HamQTH.

fdlogger_gui
  Qt desktop app, table models, operator workflows, diagnostics.

fdlogger_cli
  Export, repair, import, diagnostics, headless smoke tests.
```

The current package can remain intact while these modules are prototyped under a
new namespace. The current prototype namespace is `fdlogger_next`, which keeps
the rewrite experiment separate from the existing `fdlogger` GUI.

## Storage Model

Use SQLite as the durable local source of truth. Instead of directly mutating
contacts as the primary record, store an append-only event stream:

- `qso.created`
- `qso.updated`
- `qso.deleted`
- `sync.received`
- `sync.acknowledged`

Each event should include:

- event UUID
- station UUID
- operator call
- wall-clock timestamp
- local monotonic sequence number
- payload JSON
- sync status

A materialized QSO table can be rebuilt from the event stream and optimized for
GUI display, duplicate checks, and export generation.

## Sync Model

Multicast is useful for discovery, but should not be the only transport for
reliable QSO sync.

Suggested design:

1. Use multicast or mDNS to find peers or a hub.
2. Use TCP/WebSocket/HTTP for actual event exchange.
3. Treat each sync message as idempotent.
4. Acknowledge event UUIDs explicitly.
5. Retry with attempt counts and backoff.
6. Keep logging locally if the hub disappears.
7. Reconcile when the hub or peers return.

For small clubs, one station can act as a hub. If no hub is configured, the app
should work as a single-station logger with the same local database model.

## GUI Principles

- Main screen is the logger, not a landing page.
- Keyboard-first QSO entry.
- Clear duplicate, dirty/synced, and server-seen indicators.
- Diagnostics panel with:
  - local station ID
  - hub/peer status
  - last packet time
  - pending outbound events
  - failed retries
  - export paths
- Panic export button that always writes local ADIF, Cabrillo, and CSV.

## Test Strategy

Core logic should be testable without Qt:

- score calculation tests
- duplicate detection tests
- section parsing tests
- ADIF/Cabrillo golden-file tests
- SQLite migration tests
- event replay tests
- sync retry and idempotency tests
- packet loss/reorder simulation

Integration test helpers should fake:

- rigctld
- flrig
- WSJT-X UDP
- N1MM UDP listener
- Cloudlog responses
- QRZ/HamDB/HamQTH responses

## Prototype Status

Implemented on this branch:

- `fdlogger_next` QSO and event dataclasses.
- SQLite event log plus materialized `contacts` table.
- QSO create/edit/delete through append-only events.
- Materialized contact rebuild from replayed events.
- Store-level duplicate lookup by call, band, and mode.
- Pure score calculation against the new QSO model.
- `fdlogger-next-cli` for DB init, sample contacts, listing, scoring, and
  projection rebuilds.
- `fdlogger-next` minimal PyQt5 logger screen with add, edit, delete, duplicate
  warning, rebuild, and live score display.
- `fdlogger-next-soak` store-only synthetic load harness.
- Developer Makefile shortcuts for checks, editable pipx install, GUI launch,
  and soak runs.

Near-term remaining milestones:

1. Keyboard-speed logging pass: sticky defaults, tab order, Enter/Esc behavior.
2. Preferences for station identity, operator call, class, section, and DB path.
3. Export helpers against the new model, with ADIF/Cabrillo golden-file tests.
4. GUI soak or operator simulator using the Qt event loop.
5. Prototype hub/peer sync locally with idempotent event ingest and explicit ACKs.
6. Import existing `FieldDay.db` rows as `qso.created` events.

## Migration Notes

The current `FieldDay.db` schema can be imported by converting each existing row
into a `qso.created` event. Existing output formats should be preserved by
golden-file tests before changing export internals.
