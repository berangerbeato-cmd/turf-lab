# Audit des probabilités face au marché — 29 octobre 2026

**RECOMMANDATIONS SUSPENDUES.** Analyse descriptive exécutée sur les sorties figées ; aucun modèle réentraîné.

Les cotes PMU archivées sont des observations rétrospectives. Aucun ROI ni prix ZEturf exécutable ne peut être déduit de cet audit.

| Cohorte / cotes | Courses | Log loss modèle | Log loss marché normalisé |
|---|---:|---:|---:|
| classic_Direct | 4346 | 2.1223 | 1.8846 |
| classic_Reference | 3452 | 2.1068 | 1.9296 |
| v6_Direct | 2043 | 2.1849 | 1.9572 |
| v6_Reference | 1519 | 2.1741 | 2.0026 |

## classic_Direct

| Cote [borne basse, borne haute) | Partants | P moyenne | Gagnants observés | DQ |
|---|---:|---:|---:|---:|
| 1-3 | 2712 | 23.73% | 41.48% | 17.51% |
| 3-5 | 4703 | 16.13% | 23.35% | 20.52% |
| 5-10 | 9087 | 11.33% | 12.19% | 20.96% |
| 10-20 | 10740 | 7.77% | 5.87% | 22.22% |
| 20-50 | 12624 | 5.26% | 2.42% | 21.42% |
| 50-80 | 5639 | 3.74% | 0.66% | 21.72% |
| 80+ | 8376 | 2.45% | 0.50% | 21.01% |

diagnostic_positive_ev : 29096 chevaux, 2300.3 victoires attendues, 1162 observées. Sélection rétrospective de diagnostic, pas un backtest de paris exécutables.

diagnostic_ev_at_least_100pct : 12411 chevaux, 855.9 victoires attendues, 246 observées. Sélection rétrospective de diagnostic, pas un backtest de paris exécutables.

## v6_Direct

| Cote [borne basse, borne haute) | Partants | P moyenne | Gagnants observés | DQ |
|---|---:|---:|---:|---:|
| 1-3 | 1081 | 21.78% | 40.89% | 15.26% |
| 3-5 | 2378 | 15.32% | 21.99% | 19.51% |
| 5-10 | 4633 | 10.99% | 12.48% | 20.61% |
| 10-20 | 5317 | 7.70% | 5.85% | 19.73% |
| 20-50 | 6287 | 5.35% | 2.26% | 21.55% |
| 50-80 | 2648 | 3.78% | 1.13% | 20.73% |
| 80+ | 3410 | 2.59% | 0.50% | 21.94% |

diagnostic_positive_ev : 13487 chevaux, 1075.4 victoires attendues, 561 observées. Sélection rétrospective de diagnostic, pas un backtest de paris exécutables.

diagnostic_ev_at_least_100pct : 5632 chevaux, 407.7 victoires attendues, 126 observées. Sélection rétrospective de diagnostic, pas un backtest de paris exécutables.

## Limites et reproductibilité

- Historical PMU snapshots downloaded retrospectively. Availability at decision time unproven.
- DIRECT and REFERENCE are separate retrospective descriptors; neither is a guaranteed settlement.
- No ROI, no ZEturf execution claim, no fitting, no threshold selection.
- V6 July-October 2025 and Classic January-September 2026 are different cohorts; no model ranking.
- Intervals descriptive day-cluster bootstrap; repeated horses across days and multiple subgroup comparisons remain.
- Past DQ feature is a shrunk historical proxy, not a calibrated DQ prediction.
- Coverage cross-tabs use frozen Classic features only; V6 historic feature rows not fabricated.

Commande : `python -m scripts.audit_value_market`. Détails, exclusions, empreintes et intervalles : `audit.json`.
