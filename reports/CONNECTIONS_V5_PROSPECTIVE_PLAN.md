# Première observation prospective V5

État au 13 octobre 2026 au soir : code testé localement, collecte juillet en cours. Aucune nouvelle prédiction V5 n'est encore annoncée.

1. Terminer juillet–septembre avec contrôle qualité ≥98 % et sauvegardes.
2. Après succès du workflow de préparation, collecter octobre jusqu'à la veille du jour d'exécution. Reprendre les preuves en cache sans modifier les fichiers gelés du modèle.
3. Capturer les six premières courses françaises attelées du lendemain, triées par heure, réunion et course. Pas de remplacement des courses rejetées. Fenêtre autorisée : 14–20 octobre 2026 ; invocation unique après la préparation, pas de planification récurrente.
4. Calculer V3 et V5 combiné avec exactement les poids et le code gelés. Sauvegarder les probabilités, variables, partants, ferrure, empreintes des historiques et preuves HTTP avant départ dans predictions_v5, séparément de V1.

## Limites et étapes restantes

- Capture anticipée, pas pronostic final : les résultats du jour d'exécution sont exclus, soit une journée d'historique manquante pour les courses du lendemain. Ce décalage est enregistré explicitement ; les chiffres ne doivent pas être confondus avec le backtest disposant de tous les jours précédents.
- Les partants et équipements peuvent encore changer. Une actualisation le jour de course et une vérification des non-partants seront nécessaires avant évaluation.
- Le scoreur prospectif V5 et son suivi des arrivées ne sont pas encore activés. Aucun ROI ni résultat prospectif n'est disponible à ce stade.
- Une course déjà partie ou contenant des champs de résultat est rejetée. Les données manquantes restent inconnues. L'historique courant incomplet ou une couverture sous 98 % bloque l'exécution.
- Un échec est enregistré comme BLOCKED_NO_BET, les anciennes captures restent conservées. Aucun réentraînement, aucune recalibration, aucune mise ni promotion automatique. V1 inchangé.

70 tests locaux réussis, incluant les dates de collecte partielle, le rejet des résultats avant capture, les doublons, les probabilités normalisées et l'absence d'effet du résultat cible sur les variables.
