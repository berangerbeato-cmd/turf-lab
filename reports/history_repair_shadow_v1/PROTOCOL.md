# Turf Lab — history repair shadow v1

## Purpose
Correct historical horse performance coverage **without modifying any frozen V3, V6 or Classic model, model lock, old forecast or odds**. This experiment updates only the five recent-form features of a copy of the frozen V3 feature matrix. All other features, including Elo, connections and DQ20, remain unchanged. The candidate is not fitted or calibrated.

## Evidence rules
- Source is the signed/hashed, timestamped `individual_history_evidence` captured by the original operational run before race start. The source horse id, SHA-256 of uncompressed JSON and original collection time are verified.
- A target-day/future result is never used. Official and archive starts are matched by **date + normalized venue + race number**. Contradictions, unexplained unknown recent outcomes, fewer than five verified starts, and suspicious multiple same-day starts force abstention for the affected runner.
- Audited alias: `NANCY` = `NANCY-BRABOIS`; confirmed from matching Reims 2026-11-21 R4C5 prestart evidence, where runners 1 and 13 appeared twice because of nomenclature, not genuine missing starts.
- The candidate computes a new normalized win distribution from the original frozen V3 weights and calibrated temperature. Original V3 probabilities are reproduced first, to numerical tolerance; mismatch fails the replay.
- If the shadow result is only available after departure, it is not archived as a new prospective forecast.

## Separation
- `turf_lab/history_repair_shadow.py`: bounded replay engine.
- `scripts/evaluate_history_repair_shadow.py`: paired retrospective audits using the first original captured prediction for each race and independently stored outcomes. Outputs under `reports/history_repair_shadow_v1/replays_corrected/` and `batch_summary.json`.
- `scripts/run_prediction_request.py`: best-effort sidecar created **after** original frozen prediction but **before** the race. Output under the original prediction folder `history_repair_shadow_v1.json`. The main model, odds comparison, and daily paper-ticket protocol cannot be changed by this shadow. Errors are recorded as `UNAVAILABLE`, not hidden.
- The prestart sidecar must be scored using outcomes only after the race, and never used to recommend a real wager.

## Initial retrospective paired audit (21 November 2026)
- 11 eligible archived predictions; 11 successful replays; 9 races with usable results, 2 pending.
- Sports V3 baseline vs patch-v1: log loss 1.97306 vs 1.95914; Brier 0.76808 vs 0.76499; top-1 both 3/9.
- Mean overlaps of actual top-4 1.56 vs 1.78; actual top-5 2.33 vs 2.56. No exact top-4 or top-5 hits in either model on those nine.
- These samples are **not** an independent untouched test. The patch was designed after examining Reims, which is included in the nine. Results are descriptive only, not generalizable; no value/ROI measured.
- Historical PMU individual information remains incomplete in some cases; candidate abstention counts and failures are archived for every runner.

## Decision gates before promotion
1. Collect a new date-scoped, deterministically chosen **prospective** cohort of genuine prestart sidecar forecasts. Do not selectively evaluate only races where the correction seems helpful.
2. Require complete independently verified outcomes with unchanged runner statuses and identities; score both candidates on the same races.
3. Compare mean log loss, Brier, calibration/ECE, top-1, Top4/Top5 overlap and uncertainty clustered by race day; report missingness and abstention rates.
4. Only separately develop and test any probability/odds correction with real before-start ZEturf quotes, and confirm actual operator payouts before claiming positive EV/ROI.
5. Keep `config/recommendation_policy.json` at `SUSPENDED` until a separate reviewed decision; do not promote or optimize on the exploratory batch.
