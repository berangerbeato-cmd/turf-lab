# Mélange V6 et XGBoost regroupé — essai exploratoire

**Validation déjà consultée. Aucun réentraînement, aucune mise, aucun changement du suivi réel.**
1611 courses. Poids testés prépubliés : 0 %, 10 %, 20 %, 30 % de XGBoost.

| Part XGBoost | Log loss mensuelle moyenne | Brier | Gagnant premier |
|---|---:|---:|---:|
| 0% | 2.20985 | 0.86069 | 23.9% |
| 10% | 2.21098 | 0.86052 | 24.0% |
| 20% | 2.21347 | 0.86069 | 23.6% |
| 30% | 2.21723 | 0.86119 | 23.7% |

Poids retenu selon le critère prépublié : 0% de XGBoost.

Complémentarité des premiers choix : {"both_correct": 260, "v6_only_correct": 125, "xgboost_only_correct": 99, "both_wrong": 1127}

Intervalles et résultats mensuels dans le JSON. Les premiers choix différents ne garantissent pas un meilleur mélange de probabilités.
Tout gain éventuel nécessite une nouvelle période indépendante. Aucun ajustement supplémentaire après lecture.
