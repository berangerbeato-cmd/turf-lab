# Incident de collecte des cotes — 14 octobre 2026

Le cron configuré toutes les cinq minutes a produit des exécutions à 11:58,
12:32, 13:12, 13:48, 14:14, 14:48, 15:17 et 15:57 UTC. Les fenêtres de
capture de 20 à 5 minutes avant départ ont toutes été manquées par ces exécutions.
Un workflow vert ne prouve donc pas qu'une capture a eu lieu.

Une capture locale R1C2 a bien été validée à 12:20:57 UTC (14:20:57 Paris),
avant le départ de 14:30. Elle est restaurée avec son fichier original,
son manifeste et ses réponses brutes, sans changement d'horodatage. Elle n'avait
pas été synchronisée lors de l'échange de l'après-midi. Aucune cote a posteriori
ne remplace les cinq autres captures manquées.

## Correctif séparé du modèle

- Le cron ponctuel du 14 octobre est désactivé.
- Sessions résidentes de 310 minutes, lancées à 06:17, 11:17 et 16:17 UTC,
  uniquement du 15 au 31 octobre 2026 (garde annuelle dans le code).
- Contrôle local toutes les 60 secondes pendant les sessions ; une seule session
  à la fois, sans verrouiller les autres collecteurs du dépôt pendant l'attente.
- Sidecar limité aux prévisions valides du plan de cohorte déjà figé : aucune
  sélection supplémentaire, aucun changement des modèles ou de leur protocole.
- Maximum cinq tentatives espacées de deux minutes par course, vingt courses,
  deux requêtes par tentative : au plus 200 requêtes PMU par jour.
- Fenêtre pré-départ, fraîcheur, identité, driver, entraîneur, ferrure et absence
  de résultats conservés. Première capture valide immuable et tentatives tracées.
- Commit et envoi après chaque tentative ; échec de publication = échec du job,
  avec copie de secours en artifact Actions conservée trente jours.

Limites : GitHub peut encore retarder le lancement d'une session ou être
indisponible. Ce correctif réduit la dépendance à la ponctualité de chaque cron,
mais ne garantit pas une couverture parfaite. Les absences de plan/prévision
sont visibles dans les logs ; les créneaux manqués et rejets dans les états par
course. Une validation réelle avant départ reste à constater le 15 octobre.
Pas de mises, pas de calcul de rentabilité, pas de réentraînement.
