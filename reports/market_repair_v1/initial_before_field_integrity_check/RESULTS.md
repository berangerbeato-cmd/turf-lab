# Correction expérimentale des probabilités

**Recherche uniquement — recommandations suspendues.**
Ajustement sur 4351 courses de 2025 ; évaluation chronologique sur 3415 courses de 2026, déjà inspectées. Aucun nouveau test vierge.

Poids [log marché, log Classic] : [0.9477510618342591, 0.2959286736741781].

| Variante | Log loss (plus bas = mieux) | Brier | Premier choix gagnant |
|---|---:|---:|---:|
| classic_frozen | 2.10591 | 0.84313 | 26.59% |
| market_normalized | 1.93048 | 0.79783 | 34.17% |
| market_calibrated | 1.92477 | 0.79940 | 34.17% |
| candidate | 1.91111 | 0.79800 | 34.55% |

## Calibration par cote de référence PMU

| Cote | Classic prévu | Nouveau prévu | Observé |
|---|---:|---:|---:|
| 1-3 | 24.85% | 45.86% | 40.85% |
| 3-5 | 17.14% | 23.74% | 24.27% |
| 5-10 | 11.98% | 12.17% | 14.03% |
| 10-20 | 7.73% | 5.85% | 5.95% |
| 20-50 | 4.73% | 2.46% | 2.18% |
| 50-80 | 2.98% | 1.08% | 0.69% |
| 80+ | 2.03% | 0.59% | 0.16% |

## Limites

- 2026 evaluation outcomes already examined: reused chronological evaluation, not a virgin holdout
- PMU archive retrieval is retrospective even when the internal quote timestamp precedes departure
- PMU reference prices do not establish ZEturf live execution or settlement returns
- No odds-selected ROI claim and no new hyperparameter search after evaluation
- Individual histories are supplemental diagnostics; frozen model vectors remain unchanged

Le candidat utilise explicitement les cotes. Ce n’est pas une estimation sportive indépendante. Les cotes complètes d’un même opérateur sont indispensables. Aucun ROI calculé.

Paramètres figés avant chargement de 2026. Aucune promotion automatique ni modification de V6/Classic.
