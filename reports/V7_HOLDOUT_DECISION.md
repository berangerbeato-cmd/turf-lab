# Décision après le test indépendant V7 — 14 octobre 2026

Les trois étapes GitHub (septembre, octobre, comparaison) sont terminées avec succès.

| Indicateur, 1 062 courses | V6 | V7 |
|---|---:|---:|
| Log loss | 2,25100 | 2,24872 |
| Brier | 0,86354 | 0,86320 |
| Gagnant classé premier | 24,2 % | 23,4 % |

Écart apparié de log loss V7−V6 : −0,00227. Intervalle descriptif par journées : [−0,01445 ; +0,00909]. Le gain exploratoire n'est pas confirmé sur ce test indépendant. Ce résultat ne prouve pas non plus l'absence de tout effet.

Décision : V6 reste référence. V7 reste un challenger figé, sans correction opportuniste ni nouvelle variable. Aucune rentabilité établie. Les six captures avant-course du 14 octobre sont confirmées pour V5/V6/V7.

## Nouveau suivi prospectif prédéfini

Du 15 au 31 octobre 2026, au maximum 20 courses par jour (340 au maximum). Sélection déterministe répartie entre les premières et dernières heures du programme français de trot attelé, selon les filtres existants ; pas de remplacement des captures rejetées. Il s'agit d'une répartition des horaires publiés, pas d'une garantie d'équilibre des hippodromes.

Chaque prédiction V6/V7 est calculée avant départ avec un historique strictement antérieur à la journée. Champs modifiés ou arrivées ambiguës : exclusion visible, jamais de renormalisation après résultat. Pas de réentraînement ni de promotion automatique.

La capture est programmée à 06 h UTC : 08 h Paris jusqu'au 24 octobre, puis 07 h après le changement d'heure. Le score est programmé à 21 h UTC : 23 h puis 22 h Paris. GitHub peut retarder ou manquer un lancement ; les jours sans plan et les captures manquantes restent visibles. Le suivi des résultats s'arrête le 3 novembre inclus. La durée ne dépend pas des performances.

Budgets par exécution : 1 programme et au maximum 20 listes de participants ; historique plafonné à 1 800 requêtes avec cache ; résultats plafonnés à 120 requêtes communes aux deux modèles. Aucun endpoint de cotes, aucune mise.

Le bilan final devra distinguer toutes les courses prévues, capturées, rejetées, en attente et évaluées. La calibration et la stabilité ne se jugeront pas sur quelques gagnants isolés. Les cotes manuelles et la simulation de rendement viendront dans une étape distincte.
