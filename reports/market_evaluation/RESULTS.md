# Market probability baseline

Value and profitability are NOT established. No real bets.
Common test cohort: 3015 of 4661 races.

| Model | Market | Hit rate of most probable ticket | Predicted rate | Binary Brier |
|---|---|---:|---:|---:|
| classic | win | 25.94% | 25.48% | 0.06611 |
| classic | place3 | 49.05% | 60.97% | 0.15999 |
| classic | pair_place3 | 18.11% | 25.61% | 0.03714 |
| classic | pair_top4 | 25.84% | 41.65% | 0.07075 |
| xgboost | win | 24.41% | 26.37% | 0.06638 |
| xgboost | place3 | 48.39% | 63.07% | 0.16303 |
| xgboost | pair_place3 | 17.38% | 27.80% | 0.03755 |
| xgboost | pair_top4 | 25.54% | 44.88% | 0.07204 |
| ensemble | win | 25.27% | 25.38% | 0.06600 |
| ensemble | place3 | 47.76% | 61.01% | 0.15988 |
| ensemble | pair_place3 | 18.04% | 25.69% | 0.03714 |
| ensemble | pair_top4 | 25.90% | 41.85% | 0.07079 |
| uniform | win | 5.41% | 7.76% | 0.07141 |
| uniform | place3 | 17.01% | 23.27% | 0.17720 |
| uniform | pair_place3 | 3.52% | 4.03% | 0.03851 |
| uniform | pair_top4 | 7.40% | 8.06% | 0.07342 |

## Limits
- Rank/placement extension not trained or calibrated for these markets; IIA/strength assumptions may fail, especially DQ.
- 2026 holdout previously inspected; exploratory only. No new fitting or model selection on test.
- Common retrospective cohort: 10-20 runners, no non-runners, unambiguous top4. Actual ZEturf market opening/availability unverified.
- No time-stamped ZEturf pre-race quotes or final dividends joined: no EV/ROI/drawdown claim.
- Maximum-probability tickets do not identify value; reciprocal probabilities are model thresholds, not validated fair prices.
- Binary metrics have different base rates across markets: compare models WITHIN a market, not raw Brier across markets.
- Loss streaks follow date/race-id order, not guaranteed intraday chronological order; bets on one race are correlated.
