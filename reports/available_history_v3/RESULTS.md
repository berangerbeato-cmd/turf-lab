# Available history V3 — exploratory full-data experiment

All 17,532 training races used; no additional collection. Production unchanged. No betting recommendation.
2025 first half selects the variant; second half calibrates. 2026 was previously examined, not a virgin holdout.

Selected before test: **last5_available_dq20**.

| Model | Test races | Log loss | Brier | Top 1 | ECE |
|---|---:|---:|---:|---:|---:|
| classic_recalibrated | 4661 | 2.125915 | 0.847014 | 26.37% | 0.004624 |
| last5_available | 4661 | 2.116738 | 0.844183 | 26.80% | 0.004170 |
| last5_available_dq20 | 4661 | 2.115859 | 0.844000 | 26.93% | 0.004462 |
| classic_operational | 4661 | 2.127534 | 0.846505 | 26.37% | 0.005794 |
| v6_operational | 4661 | 2.172167 | 0.854913 | 24.93% | 0.005641 |

Paired weekly bootstrap intervals and monthly results: evaluation.json. No automatic promotion.
Operational V6 uses its actual frozen weights and annual history reset, not the continuous-history Classic inputs.
