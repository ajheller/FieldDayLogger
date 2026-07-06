# FieldDayLogger Next Soak Testing

`fdlogger-next-soak` runs a store-only synthetic load against the rewrite
prototype. It continuously creates, edits, and soft-deletes QSOs, periodically
rebuilds materialized contacts from the event log, recreates the store handle to
simulate app restarts, and checks that replayed event state matches the
materialized contact table.

The command writes JSONL samples with operation counts, QSO counts, score,
latency, RSS, rebuild count, restart count, and integrity check count.

## Short Smoke Test

```bash
fdlogger-next-soak soak.db \
  --seconds 60 \
  --rate 120 \
  --check-interval 10 \
  --rebuild-interval 15 \
  --restart-interval 20 \
  --log soak.jsonl
```

## 36 Hour Laptop Soak

```bash
fdlogger-next-soak soak.db \
  --hours 36 \
  --rate 30 \
  --check-interval 60 \
  --rebuild-interval 300 \
  --restart-interval 7200 \
  --log soak.jsonl
```

For faster abuse, raise `--rate`. For deterministic reruns, pass `--seed`.

## Reading Results

Each line in `soak.jsonl` is a standalone JSON object. The most important fields
are:

- `operations`: total synthetic create/edit/delete operations.
- `events`: total append-only events in SQLite.
- `active_qsos`: non-deleted QSOs in the materialized contact table.
- `total_qsos`: all QSOs, including soft-deleted ones.
- `avg_latency_ms` and `max_latency_ms`: operation latency.
- `rss_kb`: process max resident set size.
- `checks`: integrity checks completed.

Any replay/materialized mismatch raises an error and stops the run.
