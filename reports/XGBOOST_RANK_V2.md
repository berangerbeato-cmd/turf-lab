# XGBoost Rank V2 — sélection chronologique

**NO BET. Aucun changement V6/V7. Évaluation 2025 exploratoire.**
Quatre variantes et trois températures ; choix exclusivement sur deux fenêtres chronologiques de 2024. Groupes = courses, vainqueur = 1, autres = 0.
Sélection : {"candidate": "ndcg_depth3", "temperature": 1.0, "fold_log_losses": [2.331257814125789, 2.3048658080284725]}

Entraînement final : 1563 courses ; évaluation : 1611 courses.

| Modèle | Log loss mensuelle moyenne | Brier | Top-1 |
|---|---:|---:|---:|
| v6 | 2.20985 | 0.86069 | 23.9% |
| xgboost_rank | 2.27927 | 0.87408 | 22.3% |

Comparaison appariée : {"delta_log_loss": 0.06963558066631623, "day_bootstrap_95_percent": [0.051936589515391755, 0.0869019880805499], "days": 91, "interpretation": "Exploratory reused validation only; not an independent test."}

Un score de classement n’est pas une probabilité. La conversion softmax et sa température sont figées avant évaluation 2025 ; la calibration reste à vérifier.
Aucun test indépendant nouveau chargé, aucun ajustement après évaluation. Les périodes déjà consultées ne deviennent pas des tests vierges.
Documentation : https://xgboost.readthedocs.io/en/release_3.0.0/tutorials/learning_to_rank.html
