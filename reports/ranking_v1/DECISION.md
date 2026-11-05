# Décision : modèles de classement et combinaisons

Quatre candidats entraînés ; comparaison achevée sur 4 574 courses. La sélection des candidats provient de 2025, pas des résultats 2026.

| Objectif | Candidat retenu sur 2025 | Arrivées complètes | V3 | Écart, intervalle exploratoire 95 % |
|---|---|---:|---:|---:|
| Top3 | top4 | 195 | 238 | -0.94 point [-1.48 ; -0.35] |
| Top4 | v3 | 115 | 115 | 0.00 point [0.00 ; 0.00] |
| Top5 | rank | 88 | 79 | 0.20 point [-0.17 ; 0.61] |

## Probabilités conjointes

- Top3 : 205.4 arrivées prévues, 195 observées.
- Top4 : 271.7 arrivées prévues, 115 observées.
- Top5 : 123.6 arrivées prévues, 88 observées.

## Décision

Conserver V3 comme base opérationnelle ; archiver les quatre candidats et leur sélection expérimentale. Aucun remplacement automatique sur la base du meilleur score observé après coup.
Le calcul de combinaisons et de coût existe, mais les seuils coût/probabilité sont théoriques : les probabilités conjointes restent à valider et les rapports payés/bonus ne sont pas modélisés.
Le Brier calculé sur la sélection propre à chaque modèle ne doit pas servir à les classer directement : les événements prédits changent.
Suite utile : calibration des événements conjoints sur développement seulement, comparaison sur une période future ; intégrer ensuite des rapports documentés avant toute affirmation de value.
Ne pas relancer cet entraînement pour combler quelques trous historiques. Modèles et résultats sont déjà sauvegardés.
