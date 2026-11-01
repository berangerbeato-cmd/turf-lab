# Turf Lab execution contract

When the user sends horse-race odds screenshots:
1. Read the screenshot directly, identify Paris date / official meeting / race, runner numbers/names and decimal total-return odds. Do not ask them to type visible odds. Keep unreadable fields unknown. Never infer model probabilities from prices.
2. Read reports/OPERATIONAL_MODEL_AUDIT.md and reports/operational/latest.json if present. Reference engine is scripts.predict_operational, NEVER scripts.predict_race (archived V1).
3. With a runtime, execute `python -m scripts.predict_operational --date YYYY-MM-DD --reunion R --course C` from repository root. It loads verified existing history, frozen available_history_v3 primary, V6 and Classic full benchmarks, checks SHA-256 and rejects post-start targets. No training.
4. Without a runtime but with connected GitHub write tools, update config/prediction_request.json on main with date/reunion/course and a unique request_id. Optional quotes object: race_id, operator, source_evidence (image hash or private file reference; no account balance/image publication), verified, observed_at with timezone, odds_format DECIMAL_TOTAL_RETURN, quotes [{number,name,decimal_odds}]. A push triggers predict_race.yml. Poll the run and reports/operational/latest.json; check request_status.json is SUCCESS with matching request_id, plus matching race/date/time, never reuse another request. Do not claim success while queued, failed or blocked. Workflow dispatch is not required.
5. Execute scripts.compare_operational_quotes on the actual output and transcribed quotes. Return all runners with primary available_history_v3 probabilities and EV; add benchmark columns only when useful/requested. Include implied 1/C, fair 1/P, disagreement and limitations. Do not create an ensemble probability. Quotes remain separate from features. No automated bets.
6. State the actual prediction time, exact model versions/hashes and history-through date. Recheck nonrunners/declarations when odds are newer than the field snapshot. Early tomorrow predictions omit today's results; rerun on race day.
7. For placement use only the documented calibrated Classic top choice, 10–20 runners, no nonrunner, operator-confirmed 3 paid places. This remains a legacy Classic benchmark, not a placement prediction from the new base. No extrapolation to arbitrary horses, V6 or available_history_v3. Without a verified probable quote return EV placé non calculable.
8. The daily recent_history workflow updates verified results through yesterday with visible gaps, checkpoints and prospective scoring. Do not refit weights or require perfect 2022–present continuity. Archived source files and model locks must remain intact.

Code and workflows are backed by this repository. Do not copy the repository to a second document store. An ordinary ChatGPT session without connected tools/runtime cannot execute the models; state that limitation rather than inventing predictions.

Decision 2026-10-17 (superseded for primary designation on 2026-10-31): V6 and Classic full remain frozen benchmarks. V5/V7 predictions and model files are archived; do not reactivate their workflows. Default output columns: cheval, cote, P modèle de base V3, EV modèle de base V3. Include benchmark columns only when useful/requested.


## Decision 2026-10-29 — recommendations suspended

Read `config/recommendation_policy.json` and `reports/value_audit_2026-10-29/RESULTS.md`
before any odds analysis. Do not recommend a horse, ticket, stake, or real-money
strategy while suspended, even when both models agree or an EV is very large.
Frozen calculations, all-runner tables and paper observation remain available as
research only. Positive EV is not an eligibility signal. Do not convert archived
PMU post-race prices into executable prestart prices or a betting ROI.
Do not silently resume recommendations; resumption needs a separately validated
protocol and explicit review. Do not alter model weights or archived forecasts
to repair the losing race. Track confirmed stakes separately from suggested ones.

## Decision 2026-10-31 — user-selected base model

The user explicitly selected `available_history_v3` (`last5_available_dq20`) as the base model for subsequent work and predictions. `config/active_model.json` is authoritative. Execute `scripts.predict_operational` as before; it now computes this primary with its exact frozen feature variant, weights and late-2025 temperature. V6 and Classic are historical benchmarks, not the primary. No ensemble or silent fallback. A model promotion does not lift the recommendation suspension. The new base has no validated placement calibrator: any retained Classic placement output is explicitly a legacy benchmark. Old prediction files retain their original model labels and probabilities.

## Scope decision — 2026-10-31
Only simple gagnant, tiercé, quarté and quinté are in scope. Do not propose or develop simple placé, couplés or 2sur4. Historical placement artifacts are archival only. Prioritize calibrated value and total combination cost. An archived price is not an executable quote or a settlement. Recommendations remain suspended. Start with the active-model SG value diagnostic in reports/value_active_v1.

## 2026-11-01 — prospective SG correction shadow
Operational quote comparisons include a separate value_shadow block when the complete fresh field qualifies. Never present this market-informed correction as the independent sports primary. PRESTART_SHADOW only qualifies for prospective evaluation; retrospective replays do not. Recommendations remain suspended. Read reports/value_correction_v2/PROSPECTIVE.md for scope and limitations.
