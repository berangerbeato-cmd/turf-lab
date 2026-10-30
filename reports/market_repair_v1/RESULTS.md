# Correction expérimentale des probabilités

**Recherche uniquement — recommandations suspendues.**
Ajustement sur 3426 courses de 2025 ; évaluation chronologique sur 2578 courses de 2026, déjà inspectées. Aucun nouveau test vierge.

Poids [log marché, log Classic] : [0.9641648865516633, 0.27123652036913015].

| Variante | Log loss (plus bas = mieux) | Brier | Premier choix gagnant |
|---|---:|---:|---:|
| classic_frozen | 2.11508 | 0.84391 | 26.57% |
| market_normalized | 1.94119 | 0.80208 | 33.59% |
| market_calibrated | 1.93676 | 0.80432 | 33.59% |
| candidate | 1.92352 | 0.80217 | 33.98% |

## Calibration par cote de référence PMU

| Cote | Classic prévu | Nouveau prévu | Observé |
|---|---:|---:|---:|
| 1-3 | 24.80% | 45.78% | 40.74% |
| 3-5 | 17.01% | 23.55% | 23.68% |
| 5-10 | 11.86% | 12.00% | 13.89% |
| 10-20 | 7.71% | 5.73% | 5.84% |
| 20-50 | 4.64% | 2.37% | 2.16% |
| 50-80 | 2.86% | 1.00% | 0.60% |
| 80+ | 1.89% | 0.50% | 0.09% |

## Limites

- 2026 evaluation outcomes already examined: reused chronological evaluation, not a virgin holdout
- PMU archive retrieval is retrospective even when the internal quote timestamp precedes departure
- PMU reference prices do not establish ZEturf live execution or settlement returns
- No odds-selected ROI claim and no new hyperparameter search after evaluation
- Individual histories are supplemental diagnostics; frozen model vectors remain unchanged

Le candidat utilise explicitement les cotes. Ce n’est pas une estimation sportive indépendante. Les cotes complètes d’un même opérateur sont indispensables. Aucun ROI calculé.

Paramètres figés avant chargement de 2026. Aucune promotion automatique ni modification de V6/Classic.
