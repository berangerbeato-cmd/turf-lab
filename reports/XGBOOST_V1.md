# XGBoost V1 — comparaison exploratoire à V6

**NO BET. Aucun changement au suivi prospectif. Validation déjà consultée.**
Train : 1563 courses. Validation : 1611 courses. Même information en entrée : 38 variables V6.

| Modèle | Log loss mensuelle moyenne | Brier | Top-1 |
|---|---:|---:|---:|
| v6 | 2.20985 | 0.86069 | 23.9% |
| xgboost | 2.28225 | 0.87406 | 21.4% |

Comparaison appariée : {"delta_log_loss": 0.07268015288353652, "day_bootstrap_95_percent": [0.05454875386801306, 0.09186770201718669], "days": 91, "interpretation": "Exploratory reused validation only; not an independent test."}

200 arbres, profondeur 3, un seul réglage prépublié. Objectif binaire pondéré par course, puis normalisation des odds entre partants. Pas de réglage de calibration ni de température.
Ce premier essai ne constitue pas une recherche exhaustive du meilleur XGBoost. L’objectif binaire diffère de la log loss conditionnelle de V6.
Aucun résultat juillet–octobre 2025 ni 2026 chargé. Nouveau test indépendant nécessaire avant toute conclusion de gain.
Documentation : https://xgboost.readthedocs.io/en/stable/parameter.html
