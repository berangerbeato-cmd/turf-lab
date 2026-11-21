# Turf Lab — post-race diagnostic — 2026-11-21 R4C5 Reims

## Evidence and provenance
- User-provided screenshot `IMG_2662.jpeg`: ZEturf Z4 ticket `[2,3,6,10]`, stake EUR 1, displayed result `[2,1,11,9,4,3,7]`. Settlement of this Z4 is a loss inferred from result; no standalone payout receipt. Recorded separately in `reports/manual_bets/2026-11-21_R4C5_Z4.json`.
- All 14 runners and ZEturf odds at 18:27 CET transcribed in `config/prediction_request.json` request `chat-20261121-r4c5-1827-v3` and archived `predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z/`.
- Primary V3, V6 and Classic calculated at 18:30:23 CET before 18:37 start. Verified request status SUCCESS run [44930268127](https://github.com/berangerbeato-cmd/turf-lab/actions/runs/44930268127); source `reports/operational/latest.json` at that request.
- Frozen V2 position-specific ranking shadow predicted 17:50:18 CET; source `reports/stage_ranking_shadow/forecasts/2026-11-21/R4C5.json` (independent prestart snapshot).
- Outcome below is based on the user's screenshot, not an independently acquired official complete finish; ranks beyond the shown first seven are unknown. No inference about disqualifications or exact ranks of numbers 6 and 10.

## Before-start predictions versus displayed finish

Displayed ranks 1–7: **2 – 1 – 11 – 9 – 4 – 3 – 7**.

| Approach | Prestart top 4 | Hits in actual top 4 | Prestart top 5 | Hits in actual top 5 |
|---|---|---:|---|---:|
| Primary V3 by win probabilities | 6,4,3,12 | 0/4 | 6,4,3,12,2 | 2/5 (2,4) |
| Stage ranking V2 | 6,3,10,2 | 1/4 (2) | 6,3,10,2,1 | 2/5 (2,1) |
| User Z4 | 2,3,6,10 | 1/4 (2) | n/a | n/a |

**Winner number 2 (KLARISSA)** had prestart winning probability:
- primary V3: 7.3329% (V3 rank 5)
- V6 benchmark: 10.8898%
- Classic benchmark: 7.9672%
- value-correction V2 market-informed experimental: 9.7969%
- ZEturf market normalized implied probability 10.5137% (not a validated real-world winning probability)
- Screenshot decimal total-return win odds: 8.1

Numbers 1 and 9 were 2nd and 4th, and were among the model-history-warning runners. This is a hypothesis for data-quality investigation, not causal evidence. The complete warning list for this race is **1,5,9,10,13**.

## Reproducible operational diagnosis

### 1. Critical data coverage gap, already detected but not used
- `scripts.predict_operational.run` calls `compute_all(history,target)` **before** `individual_history_check.check_all(target,models,...)`.
- `turf_lab/individual_history_check.py` reconciles dated individual PMU performances and returns missing starts, but deliberately does not alter the frozen model feature vectors.
- For R4C5, number 1 has a missing 2026-11-15 Nancy performance in the individual history window; number 9 also has a history warning (see saved prediction diagnostics for details).
- **Research implementation candidate**: construct an explicitly versioned, time-corrected feature pipeline from verified individual histories for all runners, prior to prediction. Restrict data to timestamp strictly before the target. Never change historical V3 coefficients, model locks or post-hoc predictions.
- **Controls**: horse ID + date + venue + race number identity, duplicate detection, ATTELE only, proper DQ mapping, no future/outcome leakage, source response checksum, missingness by track and month, explicit abstention when uncertain. Validate whether enhanced data *actually* improves log loss/calibration on a new chronological holdout against locked V3 before promotion.

### 2. Primary win probabilities and value
- `reports/value_audit_2026-10-29/RESULTS.md` shows old frozen sports models underweight short-odds favorites and overweight longshots. Those historical results are not by themselves direct calibration statistics for the active available-history V3; run an equivalent properly time-scoped active-V3 analysis.
- Reims V3 raw SG EV was +20.7% on #6, +240.5% on #12, +455.6% on #8. Value-correction V2 shadow SG EV was respectively **−0.9%, −10.5%, −32.4%**; *none* of the 14 horses had positive shadow EV. This is not proof of a perfect no-bet signal based on one race.
- `reports/value_correction_v2/RESULTS.md`: hybrid had log loss 1.924891 vs raw sports 2.108413 and market normalized 1.941194 on 2,578 already-examined 2026 races. However it was fitted against historical PMU reference odds; extrapolation to live ZEturf and executable returns has not been validated.
- **Research candidate**: segment by observed-odds bands (especially 20–50, 50–80 and 80+), compare model, market and hybrid calibration plus tail outcomes using archived **prestart** quotes only. Evaluate differences with day-clustered uncertainty. Separate EV-positive counts from verified paid-return ROI; include all losing selections.

### 3. Ranking / Z4 / ZE5
- `reports/stage_ranking_shadow/scores.json` (as of 2026-11-21): 44 settled eligible races, stage selector correctly predicted 2 exact unordered top-4 combinations and 0 exact unordered top-5. V3 selector also hit 2/44 top-4 and 0/44 top-5 on the same 44; no evidence from that sample that stage selector is superior for exact combinations.
- **Research candidate**: add reproducible top-4/top-5 overlap@k (0…k), exact match, winner/top-1, optional graded order metrics, calibration of predicted exact-set probabilities and confidence intervals. Compare selectors on *identical* independently collected races. Do not choose a new winner from Reims retrospectively.
- The V3 top-five-by-win-probability is a heuristic, not a separately calibrated joint quinté result. ZE5 profitability requires operator-confirmed payouts, not only exact hit rates.

## Execution order and non-negotiable validation
1. **Data reliability first**: fix the *research* chronology for individual horse histories, audit coverage by venue, and run time-locked independent comparisons; do not modify deployed frozen V3 until robust improvement is observed.
2. **Calibrate active-V3 / value second**: demonstrate that an amended probability model beats baseline market/PMU/ZEturf on independent prestart quotes, especially in longshot odds buckets. Apply conservative abstention if validation fails.
3. **Rank-model scoring third**: continue prospective stage-ranking collection. Report overlap@4 and overlap@5 along with exact outcomes and uncertainty; 44 races are insufficient for confident promotion.
4. **Only then test frozen paper staking strategies**: one declared stake schedule and full operator payout ledger, sufficient genuinely prospective chronological data, explicit independent review before real money recommendations. Policy in `config/recommendation_policy.json` remains SUSPENDED.

No new model trained, model weights changed, or retrospective prediction rewritten by this report. No retrospective odds treated as executable prestart prices.
