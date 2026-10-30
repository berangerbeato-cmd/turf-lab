# Rapprochement des résultats sportifs — 30 octobre 2026

Reprise de la PR 5, sans nouvelle collecte : les 27 performances sans rang exploitable (26 partants cibles) ont été recherchées dans les archives quotidiennes et mensuelles existantes. L'identification exige date, code hippodrome, numéro de course, identifiant du cheval et nom concordants. Un rang doit concorder avec l'ordre d'arrivée définitif.

| Résultat du contrôle | Performances |
|---|---:|
| Incident confirmé par les résultats officiels | 2 |
| Course retrouvée, résultat individuel encore incomplet | 8 |
| Aucun résultat officiel correspondant dans les archives examinées | 17 |

Les deux incidents confirmés sont NAMARA D'ECHAL, arrêtée le 26 septembre à Enghien, et NYX ERGEE, tombée le 14 septembre à Lisieux. Ce sont des départs sans victoire et sans top 3, mais pas des disqualifications. Aucun rang numérique ne leur est attribué. Les données exportées et les modèles gelés ne sont pas réécrits par ce diagnostic.

Les huit résultats incomplets ne sont pas des contradictions prouvées : l'archive ne permet simplement pas de reconstituer un rang individuel. Les 17 absences ne prouvent pas que la course n'a pas eu lieu. Aucun cheval ni aucune course cible n'est supprimé du jeu de faisabilité.

## Conséquence pour la suite

La vérification des seuls résultats archivés ne répare pas les 24 mentions PLACE sans rang. Ne pas attendre un historique exhaustif : la prochaine version expérimentale devra conserver explicitement les résultats inconnus et les indicateurs de couverture, distinguer arrêt/chute/DQ, et mesurer la sensibilité aux données manquantes. Les fenêtres courtes des jeunes chevaux restent d'origine indéterminée (début de carrière ou source tronquée) ; ne pas les exclure automatiquement.

Avant un réentraînement : préparer un export sportif versionné appliquant ces règles, conserver toutes les courses dans un registre, fixer les périodes chronologiques et vérifier l'absence de réutilisation des tests déjà observés. Les cotes restent exclues des variables et de la sélection du modèle sportif. Les 34 courses déjà inspectées servent au développement et au contrôle des données, pas à une validation indépendante.

## Preuves

- Commande sans réseau : `python -m scripts.reconcile_sport_outcomes`.
- `reconciliation.json` conserve les décisions et empreintes des archives correspondantes, du manifeste individuel et du jeu source.
- Jeu source inchangé : `7e90a41649713b24a4044bfc60d4526291bd7fa1258207b4bb4f466492b11219`.
- Suite complète : 209 tests exécutés, aucun échec, 5 ignorés.
- Aucun réentraînement, aucune performance nouvelle annoncée, recommandations toujours suspendues.
