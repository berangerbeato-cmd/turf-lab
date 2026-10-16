# Daily history contract

Scope: PMU-listed French harness races from 2022-01-01 through yesterday in Europe/Paris.
The existing monthly partitions, raw evidence and frozen models are retained unchanged.

`python -m scripts.sync_history` verifies every calendar date and repairs only incomplete
races or missing programmes. `--audit-only` performs no HTTP requests. The old
`python -m scripts.refresh_recent_history` entrypoint delegates to the same implementation.

Programmes define the expected race IDs. Stored partitions are checked against their
SHA256 and programme; participants and final official results pass quality checks.
Official cancellations require both cancellation flags and no arrival. Dead heats count
as complete archival results, although the frozen single-winner predictor excludes them.
An absent programme means an unknown race count, never zero races.

Repairs are atomic daily overlays under `data/history_updates`, with timestamped raw
responses under `evidence/history_updates`. Verified races are reused, including those
on otherwise incomplete dates. Monthly sources are never overwritten. Recent-day
snapshots from the previous collector are reused. The report is regenerated from the
actual records, not the previous workflow status or the previous report.

A bounded 800-request pass processes recent gaps first and continues older recovery on
subsequent schedules. Transport errors, rate limits and denied access stop that batch.
Incomplete official responses remain explicit pending races. No seven-day cutoff.
Checkpoints and reports are committed even when the command exits nonzero.

The workflow on main checks out the existing research/full-year-history-2022-2026 data
branch. Schedule: 06:00 Europe/Paris, with retries at 08:30, 12:30 and 18:30. IANA timezone
scheduling handles summer/winter time. GitHub may delay scheduled execution; 06:00 is
the scheduled time, not a guarantee of exact runner start. A shared concurrency group
serializes the history writer. Pushes are rebased without force; conflicts fail visibly.

`reports/history_sync/status.json` and `status.md` distinguish last complete day, last
collected day and uninterrupted coverage from 2022. OK requires every expected date and
race; any unresolved gap produces PARTIEL and a failing workflow. Unexpected exceptions
produce ÉCHEC. Unknown-programme days are listed separately from known missing races.

Prediction loading also performs this strict audit and refuses incomplete history.
After a complete refresh, the prediction input snapshot and its checksum are updated;
past-only variables are computed by the existing `prepare` pipeline at prediction time.
No retraining, calibration changes or automatic changes to model exclusions occur.

Tests: `python -m unittest discover -s tests -p test_history_sync.py`.
