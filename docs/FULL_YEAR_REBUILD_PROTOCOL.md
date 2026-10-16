# Full-year historical coverage and fair model retest (protocol, 2026-10-14)

## Motivation
Existing V5/V6 training (March–May 2024), validation (March–May 2025), and V5 test (May–June 2026) are seasonally concentrated. No algorithm should be accepted/rejected based on this narrow distribution. Existing 2025 validation has already influenced model choices and cannot be called untouched.

## Phase 0: Inventory before any new training
Generate a machine-readable month-by-month manifest for 2022-01 through 2026-10, with expected eligible French harness trot races, retained race count, participants, unique dates, tracks, cancellations, quarantines, data completeness, source timestamps and checksums. Distinguish missing month, partial month, full month, and planned month. Do not sum overlapping datasets. Fail closed on unknown completeness.

## Phase 1: Historical backfill
Use existing bounded official PMU collectors/cache and monthly GitHub Actions checkpoints, no paid source, VPN, odds scraping or bypass. Backfill missing months chronologically, one month per job, verify 98% eligible-race coverage excluding documented cancellations, preserve raw responses, SHA-256 and quarantines. Confirm source availability before promising 2022. Keep 2026 current month explicitly partial. Never overwrite earlier evidence.

## Phase 2: Frozen evaluation protocol
Training target 2022–2024 (only if sufficiently complete), model selection 2025, chronological holdout 2026; label 2026 as previously inspected for earlier models, and reserve truly future prospective races as untouched validation. Compare identical samples/features across classic baseline, Elo/regression, XGBoost and calibrated ensemble. XGBoost is a hypothesis, not a predetermined winner. No future data leakage; fit preprocessing/calibration within each training fold; embargo where necessary. Time-ordered rolling-origin folds and monthly/seasonal reporting.

## Seasonality
Report winter/spring/summer/autumn, track, race type, field size and horse age, with confidence intervals and sample counts. Test month-of-year and cyclic month encoding against no-seasonality control. Distinguish calendar effect from venue/programme composition. Require robust out-of-time gains across seasons before adding complexity.

## Exit criteria
Coverage report and reproducible manifests; test suites passing; fair model leaderboard (log loss, multiclass Brier, top-1, calibration, per-season results); no automatic model promotion or wagering. Existing production/shadow workflows remain untouched pending independent review.
