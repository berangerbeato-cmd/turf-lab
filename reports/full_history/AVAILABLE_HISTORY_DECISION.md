# Available-history evaluation — 15 October 2026

The user authorized proceeding without chasing residual archive gaps. No more
collection retries are required for this experiment. Existing archives are retained.

## Fixed decision before results

- Keep January 2022–September 2026 as the target interval.
- Exclude November 2024 from both fitting and feature history: only November 1–6
  is available. Do not label 157/157 observed candidates as full-month coverage.
- Retain the original integrity, source verification and 98% adjusted coverage
  checks for the other 56 closed months. An integrity error remains blocking.
- Keep original chronological splits and hyperparameters. No test-driven tuning.
- Run the same classic, binary XGBoost, ranking challenger and ensemble comparison.
- Add a fixed sensitivity excluding December 1, 2024–January 29, 2025 inclusive
  from fitting/calibration. Evaluate on exactly the same 2026 test races.
- Report monthly and seasonal metrics, paired day/week intervals, rolling origins
  and calendar-feature ablation. No automatic promotion to production.

## Limits

Exclusion is not proof of absence of selection bias. Missing starts can influence
long-memory Elo beyond the 60-day buffer; the sensitivity is diagnostic only.
The 2026 test period and 2025 validation were partially inspected in prior work,
so results remain exploratory. No full 2026 autumn/winter assessment is possible.
No claim of profitability, and no real bets.
