# Turf Lab V4 : un seul résultat pour chaque course

## Ce qui change pour l'utilisateur
Une seule sortie lisible : **Turf Lab V4**. Une course et, facultativement, un tableau de cotes ZEturf complet avant départ. Les noms des versions internes (V3, V2 Cotes, Classement V2, History Repair) sont des dépendances de recherche, pas des options à choisir à chaque course.

La sortie source est `predictions_operational/<date>/<course_et_lot>/v4_unified.json`. Un résumé de la dernière demande est dans `reports/v4/latest.json`. Le format est :
- **Gagnant** : numéro, nom et probabilité estimée, avec base de calcul explicitée.
- **Top 5** : cinq numéros distincts classés.
- **Value** : statut des cotes et éventuels candidats théoriques, uniquement si une correction de cotes reproductible a pu être calculée.
- **Décision** : NO BET, systématiquement pendant l'évaluation.
- **Qualité des historiques** : liste des anomalies, sans aucune dissimulation.

## Étapes internes obligatoires
1. Calcul de la V3 gelée et collecte des historiques individuels **avant départ**, puis archivage immuable.
2. Réconciliation History Repair V1.1 obligatoire. S'il manque ou si les empreintes ne concordent pas : V4 bloquée, aucun remplacement silencieux par la V3.
3. Calcul d'une probabilité gagnant candidate après correction des cinq caractéristiques de forme. Si des cotes complètes sont disponibles dans les 15 min avant départ et ont déjà été validées par V2, la V4 affiche plutôt le candidat History Repair + V2 Cotes **non recalibré**.
4. Top 5 par Stage Ranking V2 avec les caractéristiques récentes corrigées. **Cette combinaison n'a pas encore été entraînée/calibrée conjointement** ; la seule présence d'un Top 5 ne démontre pas un profit possible sur un Z5.
5. Sortie de recherche NO BET. Les captures d'origine des modèles V3, Classement V2, V2 Cotes et leurs données sont conservées sans modification pour les comparaisons statistiques.

## Déclencher
Le workflow GitHub `.github/workflows/predict_race.yml` reste celui d'une course :
- depuis `config/prediction_request.json` contenant date, réunion, course et, si disponibles, des cotes vérifiées ;
- ou manuellement via workflow_dispatch avec date, réunion et course, sans cotes. Dans ce dernier cas, la valeur économique n'est pas calculable.

La commande existante `python -m scripts.run_prediction_request` crée **en plus** le résumé V4, sans altérer l'historique des autres sorties. Si History Repair ne peut pas être créé, la synthèse V4 indique **BLOCKED_NO_BET** et la raison.

## État scientifique réel, au 21/11/2026
**V4 n'est PAS un nouveau modèle statistique entraîné et validé.** C'est un point d'entrée unique expérimental réunissant des modèles préexistants et une réconciliation obligatoire. Le Classement V2 et les coefficients V2 Cotes n'ont pas été réentraînés sur des données History Repair. Les nouveaux calculs sont des candidats, pas des probabilités calibrées garanties.

La course de Reims du 21 novembre sert **uniquement de test de rejeu rétrospectif**, même si ses premières sources furent capturées avant départ. Une décision de promotion demanderait des comparaisons prospectives chronologiquement indépendantes, un contrôle de la calibration (log loss / Brier), du classement Top 4/5, des anomalies de données, ainsi que des cotes acceptées et rapports réellement payés avant toute rentabilité revendiquée.

**Aucun conseil de mise, aucun pari automatique, aucun retour en mode paris réels** tant que `config/recommendation_policy.json` reste à SUSPENDED.
