# Correction de couverture — 13 octobre 2026

Avant tout entraînement V2, le contrôle a bloqué janvier 2026 : 497/515.
Les 18 exclusions sont explicitement COURSE_ANNULEE et ANNULEE dans les réponses PMU.
Correction du dénominateur : courses programmées moins annulations prouvées.
Les empreintes des réponses sont vérifiées. Une arrivée contradictoire bloque cette exclusion.
Les autres quarantaines restent au dénominateur. Le seuil de 98 %, les dates,
les variables et les hyperparamètres restent inchangés. Aucun score de test consulté
avant cette correction. Aucune course annulée ne devient une observation d'entraînement.
Cette clarification du protocole est enregistrée avant l'évaluation, avec un audit par mois.
44 tests passent, dont annulation ambiguë, résultat contradictoire, corruption des preuves,
comptabilité des courses et conservation des véritables lacunes.
