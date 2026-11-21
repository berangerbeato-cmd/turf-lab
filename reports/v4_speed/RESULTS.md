# V4 + anciens chronos corrigés V7 : essai isolé

**Trois nouvelles séries de poids, sans modification de la V4 publique.**
Entraînement gagnant 17532 courses, classement 17335, cotes 1711.
Chronos antérieurs présents : train 63.6%, test 58.1%.
Les mêmes 365 coureurs historiques vérifiés restent corrigés dans les deux variantes.

## Résultats 2026 : test déjà vu, pas indépendant
| Mesure | V4 actuelle | V4 + vitesse |
|---|---:|---:|
| Gagnant log loss ↓ | 2.115676 | 2.107134 |
| Gagnant Brier ↓ | 0.844437 | 0.842512 |
| Premier cheval gagnant | 26.95% | 27.08% |
| Top5 chev. trouvés / 5 | 2.8115 | 2.8168 |
| Top5 exact | 103/4574 | 109/4574 |
| Correction cotes log loss ↓ | 1.924987 | 1.924123 |

Comparaison log loss appariée hebdomadaire : {"challenger_minus_classic": -0.008541534247628034, "interval_95": [-0.01115399919978023, -0.005928844507646967]}.

**Ne pas promouvoir automatiquement** : période de test 2026 déjà inspectée, problème d'équivalence de calcul du chrono sur les courses futures encore à vérifier, prix PMU rétrospectifs, aucun ROI ZEturf.
La V4 publique et tous ses fichiers gelés demeurent inchangés.
