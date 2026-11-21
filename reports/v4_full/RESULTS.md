# Turf Lab V4 : réentraînement complet expérimental

**Trois ensembles réentraînés** : gagnant sur 42 variables, Top5 à cinq distributions conditionnelles, correction des cotes. Aucun ancien poids V3/V2 utilisé.

Courses de sport entraînement : **17532** ; courses Top5 : **17335** ; cotes calibrées : **1711**.
Corrections historiques individuelles effectivement injectées : **365** coureurs sur **157** courses. Les archives restantes NE SONT PAS déclarées complètes.

## Évaluation 2026 réutilisée (pas vierge)

| Composant | V3/V2 figées | V4 réentraînée |
|---|---:|---:|
| Gagnant log loss ↓ | 2.11586 | 2.11568 |
| Gagnant top1 | 26.93% | 26.95% |
| Top5 chevaux retrouvés (sur 5) | 2.782 | 2.812 |
| Top5 exact | 1.73% | 2.25% |
| Correction cotes log loss ↓ | 1.92489 | 1.92499 |

**Restrictions majeures :**
- Le supplément individuel sur 618 courses a été collecté rétrospectivement, pas en 2024/2025 avant départ. Seuls les départs datant strictement d'avant la course cible ont été repris.
- L'évaluation 2026 a déjà été inspectée dans d'anciennes expériences ; aucune promotion automatique.
- Les cotes sont des archives PMU, pas des prix ZEturf acceptés ; aucune rentabilité démontrée.
- Pas de paris réels tant que la cohorte prospective V4 n'a pas établi de gain et d'absence de calibration dangereuse.
