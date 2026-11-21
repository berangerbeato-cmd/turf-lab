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


## Reprise 21 novembre : passage V1 à V1.1 et protocole prospectif
- Une ancienne réévaluation affichait artificiellement zéro course après la correction `NANCY-BRABOIS -> NANCY` : des fichiers de rejeu préexistants étaient refusés par la comparaison immuable. Ils restent archivés en `replays_corrected/` (version initiale). La correction nouvelle est une **version distincte** `history_repair_shadow_v1_1_nancy_alias`, archivée sous `replays_nancy_alias_v1_1/`. Aucun ancien résultat n'est réécrit ; les mélanges de versions ne sont pas évalués.
- `scripts/evaluate_history_repair_shadow.py` refuse désormais de publier un nouveau tableau si **aucun** rejeu ne réussit.
- `scripts/run_prediction_request.py` crée le sidecar facultatif `history_repair_shadow_v1_1.json`; il ne bloque ni les prédictions habituelles ni les comparaisons de cotes si le candidat échoue.
- `scripts/capture_history_repair_prospective.py` et workflow `.github/workflows/history_repair_cohort.yml` : à partir du **22/11/2026**, capture planifiée à 10 h 55 et 15 h 55 (Europe/Paris), au maximum deux premières courses françaises de trot attelé dont le départ reste à >=40 min, avec un maximum de quatre captures par jour, sans sélectionner selon la cote ou les performances. Durée de collecte prévue jusqu'au 22/03/2027. Les prévisions sont enregistrées séparément dans `reports/history_repair_shadow_v1/prospective_forecasts/`, sans modification de `reports/operational/latest.json`.
- `scripts/score_history_repair_prospective.py` : lit **les sidecars d'origine uniquement**, jamais un nouveau rejeu effectué après départ. Vérifie heure de capture, version, modèle V3, identité, statuts des partants, heure du départ et arrivée officielle 1-5. Les courses avec écarts sont exclues explicitement. Mesures appariées : log loss, Brier, top1, overlaps top4/top5, exacts top4/top5, intervalles bootstrap par jour après au moins dix jours.
- **Important :** les captures à la demande, potentiellement sélectionnées par l'utilisateur, ne sont **pas mélangées** à la cohorte déterministe dans les statistiques prospectives officielles.
- Les classements ne seront considérés suffisamment étudiés qu'après au moins 200 courses officielles vérifiées avec tailles d'échantillon et exclusions explicites. Ce seuil est un point de revue, pas une validation automatique ni un droit de conseiller des paris.
- La collecte régulière dépend de l'exécution effective des workflows et de la disponibilité des sources. Une configuration planifiée ne garantit pas un nombre d'échantillons ni une réussite quotidienne.
