# Backtest historique V2

**Expérimental — NO BET.**

Découpage : {"train": 496, "validation": 537, "test": 488}

| Test mars 2026 | Log loss | Brier | Top-1 |
|---|---:|---:|---:|
| selected | 2.4308 | 0.8988 | 19.9% |
| uniform | 2.5445 | 0.9197 | 6.6% |

Sélection uniquement sur mars 2025. Janvier–février servent à construire les historiques, pas à évaluer.

Le modèle prospectif V1 reste inchangé. Résultats saisonniers, historiques incomplets hors périmètre PMU ; aucune rentabilité établie.
