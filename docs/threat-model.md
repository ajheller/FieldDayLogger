# FieldDayLogger Rewrite Threat Model

This is a lightweight threat model for the rewrite prototype. It is meant to
guide design decisions before networking, imports, and status displays become
large enough to harden later at much higher cost.

FieldDayLogger is not a high-secrecy application. Most QSO data is exchanged on
the air, and Field Day logs are not usually sensitive in the way medical,
financial, or credential data is sensitive. The main security goal is to protect
log integrity, operator workflow, and recovery ability during and after the
event.

## Assets To Protect

- QSO event history.
- Materialized contact state rebuilt from events.
- Submitted exports such as ADIF, Cabrillo, and CSV.
- Station identity and operator attribution.
- Score calculations and duplicate decisions.
- Recovery metadata for imports, paper logs, OCR review, and repairs.
- Operator time and confidence during the contest.

## Assumptions

- The app often runs on a temporary club LAN.
- Internet access may be unavailable or intentionally avoided.
- Stations may be old laptops, Raspberry Pis, or mixed personal machines.
- The club may operate in a public space where unattended laptops, tablets, or
  USB drives can be lost or stolen.
- Operators may be tired, distracted, or unfamiliar with the software.
- USB drives, SD cards, and network links may be slow or unreliable.
- Most attackers are more likely to be accidents, bad packets, broken inputs,
  or misconfiguration than a determined adversary.

## Non-Goals

- Do not require cloud identity or internet access.
- Do not require heavyweight account management for ordinary Field Day use.
- Do not treat public on-air QSO details as high-secrecy data.
- Do not let security features slow normal QSO entry.

## Primary Risks

### Accidental Operator Damage

The most likely risk is a well-meaning operator editing or deleting the wrong
contact, importing the wrong file, using the wrong clock, or closing the wrong
station.

Mitigations:

- Keep QSO changes append-only and auditable.
- Preserve edit and delete events instead of destroying history.
- Provide rebuild, repair, and export-from-any-database tools.
- Prefer clear confirmation for destructive actions.
- Show station, operator, clock, and database path clearly in diagnostics.

### Malformed Input

Imports, N1MM packets, WSJT-X UDP, CSV files, paper-log transcription output,
and future sync messages may be malformed, incomplete, duplicated, or hostile.

Mitigations:

- Validate all inbound data before writing events.
- Reject invalid contest exchanges, bands, modes, timestamps, and duplicate
  event IDs.
- Treat parser failures as recoverable errors, not application crashes.
- Keep import source metadata so bad batches can be reviewed or reversed.
- Add tests with malformed, oversized, duplicated, and out-of-order input.

### LAN Event Injection

Future sync should not let any machine on the LAN mutate the log merely by
sending a plausible packet.

Mitigations:

- Use explicit station identity.
- Make event UUID ingest idempotent.
- Validate event payloads before accepting them.
- Track ACKs, retries, and source station diagnostics.
- Consider a shared club secret or signed event envelope before enabling
  multi-station mutation across the LAN.
- Keep dashboard and status-display endpoints read-only by default.

### Replay And Duplicate Delivery

Reliable sync will resend messages. Packet capture, station restart, or bad
retry logic can also replay old events.

Mitigations:

- Use event UUIDs as idempotency keys.
- Store received event IDs durably.
- Make duplicate delivery harmless.
- Rebuild from merged event logs in tests.
- Include local sequence numbers for diagnostics, but do not trust sequence
  numbers as the only ordering or authenticity mechanism.

### Corrupt Or Lost Storage

USB sticks, SD cards, laptop disks, and SQLite files can fail during the event.
Slow removable media can also expose latency problems hidden by fast local SSDs.

Mitigations:

- Keep SQLite as an inspectable local source of truth.
- Add `PRAGMA integrity_check` style diagnostics.
- Support panic export from any surviving station database.
- Encourage frequent backup snapshots during club operation.
- Keep JSONL soak logs and diagnostic bundles separate from the primary DB when
  practical.
- Test on Raspberry Pi and removable storage, not only on developer laptops.

### Physical Loss Or Theft

Field Day stations may operate in parks, parking lots, schools, or other public
spaces. A laptop, Raspberry Pi, tablet, USB drive, or paper-log folder can be
lost, borrowed, or stolen during the event.

Mitigations:

- Keep the live database recoverable from another station, hub, or recent
  backup snapshot.
- Provide a quick way to identify which station database or paper log is
  missing.
- Avoid storing API keys, service credentials, or unrelated personal files in
  the logger configuration.
- Encourage ordinary OS protections such as screen lock, user passwords, and
  disk encryption on personally owned laptops.
- Make panic export and diagnostic bundles easy to copy before leaving the
  site.
- Treat removable media as expendable and label it with club contact
  information when appropriate.

### Clock Skew

Wrong system time can produce confusing logs, broken ordering, and painful
post-event cleanup.

Mitigations:

- Store station identity and local sequence numbers with wall-clock timestamps.
- Add clock diagnostics and warnings.
- Make time repair an explicit workflow.
- Preserve original timestamps and repair events rather than silently rewriting
  history.

### Status Display Exposure

A large-screen status app is useful for a club, but it should not become a
remote-control surface by accident.

Mitigations:

- Make status display endpoints read-only by default.
- Keep operator actions in the logger app or authenticated control surfaces.
- Avoid exposing raw filesystem paths, secrets, or unnecessary host details.
- Rate-limit or bound expensive status requests.

## Design Rules

- Local logging must continue when security, sync, or network features fail.
- Append-only event history is the audit and recovery foundation.
- Every inbound boundary needs validation.
- Duplicate event delivery must be harmless.
- Network mutation should require an intentional trust mechanism before real
  club deployment.
- Read-only dashboards are safer than remote-control dashboards.
- Public-space deployments should assume a station or removable drive can
  disappear and still leave the club able to recover the log.
- Diagnostics should help a tired operator understand what happened.
- Recovery tools are part of reliability, not an afterthought.

## Later Questions

- Should club sync use a shared event secret, signed events, TLS, or a simpler
  pairing process?
- Should operator roles exist, or is station-level trust enough?
- Should backups be encrypted when stored on removable media?
- How should a station revoke trust in a misbehaving peer during an event?
- What is the minimum authentication needed for a hub without making setup
  fragile?
- Should imported paper-log or OCR batches support one-command rollback?
