# Audit des prochaines variables

Sources : 5169 courses de janvier–mai 2024/2025. Mesures sur 3174 courses et 41960 participations actives de mars–mai. Historique strictement antérieur, fenêtre 60 jours.

| Contrôle | Couverture |
|---|---:|
| Âge présent et positif | 41960/41960 (100.0%) |
| Sexe reconnu | 41960/41960 (100.0%) |
| Courses avec des âges différents | 1078/3174 (34.0%) |
| Courses avec des sexes différents | 2475/3174 (78.0%) |
| Gains carrière positifs | 30676/41960 (73.1%) |
| Gains carrière égaux à zéro (pas nécessairement absents) | 971/41960 (2.3%) |
| Gains carrière absents ou invalides | 10313/41960 (24.6%) |
| Plafond de gains reconnu par expression stricte | 2767/3174 (87.2%) |
| Champ engagement = vrai | 2/41960 (0.0%) |
| Au moins un chrono antérieur exploitable | 26705/41960 (63.6%) |
| Au moins trois chronos antérieurs | 4349/41960 (10.4%) |
| Au moins une sortie du même tandem | 16769/41960 (40.0%) |
| Au moins trois sorties du même tandem | 1946/41960 (4.6%) |

## Contrôles et décisions

Chronos de chevaux classés avec temps et distance : 30624/30624 concordent à 1 % avec temps × 1000 / distance. Cohérence empirique, pas preuve de comparabilité entre hippodromes.
- Âge/sexe : candidats à tester. Un effet identique à tous les chevaux de la course ne les départage pas ; contrôler la variation intra-course.
- Engagement : le booléen PMU est presque toujours faux. Le plafond textuel ne suffit pas : conditions annexes, recul et temporalité des gains restent à valider. Aucune conversion monétaire ou variable de ratio encore adoptée.
- Chronos : utiliser seulement les courses antérieures classées. Corriger le contexte sans données futures ; ne jamais utiliser le chrono de la course cible. Aucun chrono corrigé encore implémenté.
- Tandem : compter les sorties communes et régulariser fortement les petits effectifs ; noms de drivers potentiellement ambigus. Couverture ne signifie pas gain prédictif.

## Vérification avant-course

{"evidence_folder": "evidence/v5_shadow/20261013T185651800684Z", "counts": {"races": 6, "races_simple_gain_ceiling": 4, "runners": 82, "age_valid": 82, "sex_valid": 82, "driver_known": 82, "career_gains_numeric": 81, "current_chrono_positive": 0}, "limit": "Current field availability only; does not prove original historical publication or historical gains timing."}

Les captures du 14 octobre servent uniquement à vérifier la présence des champs avant départ. Aucun résultat 2026 chargé pour cet audit.

## Prochain essai proposé, non exécuté

Comparer V5 inchangé à V5 + âge/sexe, puis V5 + tandem, puis leur combinaison sur les données de développement. Ne pas retoucher V5 ni sélectionner avec mai–juin 2026.
Un protocole spécifique doit être figé avant calcul. Validation déjà consultée : résultats exploratoires. Réserver une nouvelle période indépendante avant toute conclusion de gain.
Différer les gains/engagement jusqu’à validation des unités et de leur temporalité ; différer les chronos corrigés jusqu’à définition et vérification de la normalisation.
Aucun modèle nouveau entraîné. Aucun changement aux prédictions V5. Aucun pari.
