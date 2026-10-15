# Available-history model comparison

Exploratory: 2025 and some 2026 outcomes were previously inspected.
Excluded training months: {"2024-11": "Only 6/30 days available after bounded recovery failed; excluded before model results, data preserved. Other 56 closed months must pass original quality checks."}
No real bets or automatic deployment.

| Model | Test races | Log loss | Brier | Top-1 | ECE |
|---|---:|---:|---:|---:|---:|
| classic | 4661 | 2.12753 | 0.84651 | 26.37% | 0.00579 |
| xgboost | 4661 | 2.15108 | 0.85206 | 24.99% | 0.00457 |
| xgboost_rank | 4661 | 2.18170 | 0.85677 | 24.67% | 0.00924 |
| ensemble | 4661 | 2.12292 | 0.84551 | 26.05% | 0.00569 |
| uniform | 4661 | 2.50361 | 0.91612 | 6.11% | 0.00000 |

Full subgroup results, calibration bins, day/week intervals and rolling-origin checks: comparison.json.
Credibility requires consistent gains across folds/seasons; confidence intervals do not prove profitability.
Autumn 2026 is September only. Future prospective validation remains necessary.
