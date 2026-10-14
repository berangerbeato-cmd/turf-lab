# V7 : chrono corrigé du contexte — essai exploratoire

**NO BET. V6 prospectif inchangé. Validation réutilisée, pas de test indépendant.**

Entraînement : 1563 courses. Validation : 1611 courses.

| Variante | Log loss mensuelle moyenne | Brier | Top-1 |
|---|---:|---:|---:|
| v6 | 2.20985 | 0.86069 | 23.9% |
| v7_speed | 2.19310 | 0.85668 | 25.3% |

Couverture de la variable : {"train": {"active": 20784, "with_speed": 13387}, "validation": {"active": 21176, "with_speed": 13304}}

Comparaison appariée exploratoire : {"delta_log_loss": -0.016619563735840462, "day_bootstrap_95_percent": [-0.02422991691195466, -0.00826295559210394], "days": 91, "interpretation": "Validation only; exploratory interval, not adjusted for selecting multiple candidates"}

Une seule variable supplémentaire. Correction partielle : hippodrome, classe de distance et départ, estimés sur les journées antérieures. Qualité de course, météo et état réel de piste restent confondus.
Aucun ajustement après lecture. Juillet–août 2025 non utilisés. Nouvelle période indépendante nécessaire pour confirmer tout gain.
