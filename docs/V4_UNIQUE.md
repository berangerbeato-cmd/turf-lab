# Turf Lab V4 unique : 47 variables (version active)

**La V4 47 variables est désormais la seule V4 présentée à l'utilisateur.** Les anciens modèles ne servent que de témoins scientifiques.

## Les quatre ajouts d'un seul coup
1. **Gains de carrière relatifs :** dernier montant de gains connu lors d'une course antérieure, relatif aux autres partants ; aucune valeur de la course cible ni montant inventé. PMU historique consulté rétrospectivement, publication précise de l'ancien montant non prouvée.
2. **Classe relative :** indice construit sur les arrivées antérieures 1er à 5e et comparé au lot ; c'est un proxy ordinal, pas une somme de gains en euros.
3. **Forme récente pondérée :** poids fixés avant le test à 35/25/18/12/10 % pour les cinq courses officiellement observées, avec disqualification traitée séparément ; inconnu conservé comme inconnu.
4. **Indice R :** complétude des cinq dernières courses, des résultats explicites, des chronos et des gains antérieurs. Une nouvelle fonction de correction des cotes **apprend** sur 2025 H2 l'impact de R plutôt que d'appliquer une décote arbitraire.

**Réentraînement conjoint des 3 composants sur 47 variables :** gagnant 17 532 courses, Top5 17 335 et cotes 1 711. Poids `models/v4_multifeature/\{winner,ranking,market\}.json` gelés par `models/v4_multifeature/frozen_before_test.json`. Les calculs 2026 demeurent exploratoires.

## Une seule chaîne pour une course
`scripts.predict_operational` produit la preuve V3 immuable ; `scripts.capture_v4_context` ajoute les preuves chronologiques des nouvelles variables, **sans toucher au code V3 figé** ; History Repair V1.1 est obligatoire ; `turf_lab.v4_multifeature_inference` calcule **une seule** sortie `v4_integrated.json` (gagnant, Top5, valeur théorique ou absence de cotes, indice R et état des sources).

Si la preuve historique requise manque ou est produite après départ, le modèle V4 ne fait **aucun fallback** vers les anciennes versions : `BLOCKED_NO_BET`.

## Résultats 2026 non indépendants
| Mesure | V4 précédente 43 | V4 complète 47 |
|---|---:|---:|
| Log loss gagnant ↓ | 2,107134 | 2,102854 |
| Top1 gagnant | **27,08 %** | 26,63 % |
| Top5 exact / 4 574 | 109 | **111** |
| Log loss cotes ↓ | 1,924123 | **1,923323** |

**Ne pas assimiler la baisse de log loss à une meilleure précision du premier choix.** Les cotes testées sont PMU historiques, pas des prix ZEturf effectivement acceptés. La cohorte prospective indépendante démarre à zéro après intégration. La politique de paris réels reste `SUSPENDED` : décision **NO BET**.

[Rapport détaillé](../reports/v4_multifeature/RESULTS.md) | [Suivi prospectif](../reports/v4_integrated/prospective_scores.json) | [Configuration active](../config/v4_active.json)

---

## Anciennes documentations conservées pour audit

# TURF LAB V4 : version active avec les chronos corrigés

**Depuis le 22 novembre 2026, Turf Lab V4 utilise réellement 43 variables.** Le signal de vitesse contextualisée de notre V7 a été intégré aux trois ensembles de coefficients réentraînés. Il n'existe qu'**une seule V4 à utiliser**.

## Fonctionnement actuel

1. La course est capturée, avec les performances officiellement connues **avant le départ**.
2. `History Repair V1.1` contrôle et réconcilie les cinq dernières performances.
3. Le calcul `v4_speed_context.json` reconstitue la **43e variable** de chacun des partants : la médiane de ses récents écarts de réduction kilométrique au chrono attendu pour l'hippodrome, la catégorie de distance et le départ, à partir **des courses antérieures uniquement**. Une performance manquante reste `null`, conformément à l'entraînement.
4. `turf_lab/v4_active_inference.py` applique les poids nouvellement entraînés de `models/v4_speed/` : probabilités de gagner, cinq positions de classement, puis correction des cotes si un tableau complet et vérifié existe.
5. Un seul rapport `v4_integrated.json`, et un seul état `reports/v4/latest.json`. Si le contrôle historique ou le contexte chrono ne peut être établi, V4 répond `BLOCKED_NO_BET` plutôt que revenir à la V4 ancienne.

**Les 42 variables précédentes sont conservées comme entrées, et la 43e les complète.** La V4 précédente, la V3, V2 Cotes et les autres références restent gelées à des fins d'audit, pas pour offrir plusieurs choix aux utilisateurs.

## Résultats et limites

Le réentraînement historique a porté sur 17 532 courses gagnant, 17 335 Top5 et 1 711 cotes. Sur l'évaluation 2026 déjà consultée, log loss gagnant **2,11568 → 2,10713** et Top5 exact **103 → 109 sur 4 574**. Correction cotes **1,92499 → 1,92412**. Ces améliorations sont **exploratoires**. Il n'existe encore aucune validation indépendante ZEturf ou ROI réel.

La validation en conditions prospectives utilise désormais `scripts/score_v4_integrated_prospective.py` et `reports/v4_integrated/prospective_scores.json`. Les tests GitHub de la nouvelle entrée ont réussi.

**Politique de mise inchangée : SUSPENDED / NO BET.** L'intégration a été explicitement demandée ; elle n'autorise pas à surestimer la qualité des probabilités ni à proposer des mises réelles.

---

## Ancienne documentation V4 (42 variables), conservée pour traçabilité

# Turf Lab V4 : un seul résultat par course

**Statut au 21 novembre 2026 : V4 effectivement réentraînée, mais encore expérimentale (NO BET).**

Pour l'utilisateur : **un seul moteur nommé Turf Lab V4**. La saisie reste une course avec, si disponibles, les cotes ZEturf complètes. La sortie produite par `scripts.run_prediction_request` est `v4_full_retrained.json`, avec copie lisible dans `reports/v4/latest.json`.

## Modèles V4 (poids neufs)
- **History Repair** : préalable obligatoire, rapproche les seules performances individuelles datées et vérifiables ; ne fabrique pas les départs manquants. 365 coureurs corrigés dans la base historique de 28 591 courses, répartis sur 157 courses. Les autres archives ne sont pas déclarées exhaustives.
- **Gagnant V4** : nouveau modèle de 42 variables, entraîné sur 17 532 courses (2022–2024), calibré début 2025.
- **Classement V4** : cinq nouveaux modèles de choix conditionnel (17 335 courses), calibrés début 2025 ; produit le Top 5 unique.
- **Correction cotes V4** : nouveaux coefficients sur 1 711 courses de juillet–décembre 2025, appliqués uniquement si les cotes vérifiées du marché sont disponibles. Sans cotes : pas de value.
- Les anciens V3, Stage V2 et V2 Cotes restent archivés comme témoins, **jamais utilisés comme coefficients V4**.

## Performance exploratoire 2026 (données déjà inspectées)
| Indicateur | Ancien | V4 réentraînée |
|---|---:|---:|
| Log loss gagnant | 2,11586 | 2,11568 |
| Précision premier choix | 26,93 % | 26,95 % |
| Top5 exact | 79/4 574 | 103/4 574 |
| Log loss avec cotes PMU | 1,92489 | 1,92499 |

**La V4 n'est pas encore prouvée meilleure.** Les améliorations gagnant sont marginales et les cotes légèrement moins bonnes. Les historiques détaillés d'avant 2026 ont été récupérés rétrospectivement et leur couverture est limitée ; aucune évaluation 2026 n'est vierge. Il faut une cohorte de prévisions réellement antérieures au départ pour valider.

## Contrôles et données
- `models/v4_full/` : nouveau gagnant, classement et marché et `frozen_before_test.json` avec empreintes SHA256.
- `reports/v4_full/evaluation.json` et `reports/v4_full/RESULTS.md` : résultats, qualité des historiques et limites.
- `scripts/train_v4_full.py` et `turf_lab/v4_retrain_data.py` : réentraînement chronologique. Ne réentraîne jamais automatiquement avec le test.
- `turf_lab/v4_full_inference.py` : un seul pronostic public expérimenté, avec History Repair obligatoire et NO BET si défaut.
- `scripts/score_v4_full_prospective.py` : scores des seules prévisions originales d'une cohorte future, sans fuite des arrivées.

**Politique** : `config/recommendation_policy.json` toujours SUSPENDED. Aucun pari automatique ou montant recommandé. Les valeurs EV et Z5 sont des métriques d'étude, pas des conseils validés.

---

## Ancien prototype unifié : archive historique

La suite ci-dessous décrit le prototype V4 antérieur au réentraînement. Il est conservé pour traçabilité uniquement. Ne plus le traiter comme le modèle de référence.

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
