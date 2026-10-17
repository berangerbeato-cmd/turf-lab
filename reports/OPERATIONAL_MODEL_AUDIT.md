> Décision du 17 octobre 2026 : seuls V6 (principal) et Classic full (comparateur) restent actifs. V5 et V7 sont désormais archivés ; les statuts opérationnels ci-dessous décrivent la situation lors de l’audit initial. Aucun poids ni résultat historique modifié.

# Audit du 16 octobre 2026

Sources examinées : main 9a8f61bb7 et research/full-year-history-2022-2026 10a55afcc.
À l'ouverture de l'audit, le README de main décrivait encore le pilote V1 (corrigé depuis). La branche recherche contient les archives étendues et d'autres modèles : l'audit ne doit pas se limiter à main.

| Modèle | Variables principales | Courses entraînement | Courses test | Log loss | Brier multiclasses | Top-1 | Statut |
|---|---|---:|---:|---:|---:|---:|---|
| V1 | cinq statistiques des sorties antérieures | 14 | 14 | 2,4845 | 0,8960 | 7,1 % | pilote entraîné/testé ; archivé, retiré du workflow manuel |
| V2 | historique antérieur des cinq dernières sorties | 496 | 488 | 2,4308 | 0,8988 | 19,9 % | entraîné/testé, archive |
| V3 combined | V2 + Elo relatif + DQ régularisée | 496 | 528 | 2,44106 | 0,89959 | 17,8 % | entraîné/testé, archive |
| V4 combined | V3 + départ + aptitude parcours | 496 | aucun indépendant | — | — | — | validation 537 courses ; non retenu |
| V3 réentraîné dans expérience V5 | architecture V3 sur échantillon élargi | 1 563 | 1 088 | 2,35859 | 0,88853 | 19,9 % | baseline V5, différent des poids V3 initiaux |
| V5 combined | V3 + driver + entraîneur + ferrure | 1 563 | 1 088 | 2,16732 | 0,85524 | 24,4 % | gelé, test indépendant ; comparaison opérationnelle |
| V6 combined | V5 + âge/sexe + tandem cheval/driver | 1 563 | 1 113 | 2,13935 | 0,85080 | 24,7 % | gelé, référence retenue |
| V6 sur test V7 | mêmes poids V6 | 1 563 | 1 062 | 2,25100 | 0,86354 | 24,2 % | baseline appariée V7 |
| V7 speed | V6 + chrono corrigé du contexte | 1 563 | 1 062 | 2,24872 | 0,86320 | 23,4 % | gelé, challenger ; gain non confirmé |
| XGBoost V1 | 38 variables V6 ; 200 arbres profondeur 3 | 1 563 | aucun nouveau test indépendant | — | — | — | abandonné ; validation 1 611 : LL 2,28225 |
| XGBoost Rank V2 | mêmes variables, ranking + température | 1 563 | aucun nouveau test indépendant | — | — | — | abandonné ; validation 1 611 : LL 2,27927 |
| Ensemble V1 | mélange V6 / XGBoost rank | modèles ci-dessus | aucun nouveau test indépendant | — | — | — | poids XGB retenu 0 % ; archive |
| Classic full history | 38 variables V6, Elo/DQ continus entre années | 17 532 | 4 661* | 2,12753 | 0,84651 | 26,37 % | gelé, comparaison exploratoire supplémentaire |
| XGBoost full history | mêmes 38 variables ; arbres binaires | 17 532 | 4 661* | 2,15108 | 0,85206 | 24,99 % | développé/entraîné/testé ultérieurement ; non retenu actif |
| XGBoost rank full history | mêmes variables ; ranking | 17 532 | 4 661* | 2,18170 | 0,85677 | 24,67 % | challenger archivé |
| Ensemble full history | mélange classique/XGBoost sélectionné en 2025 | modèles ci-dessus | 4 661* | 2,12292 | 0,84551 | 26,05 % | exploratoire ; pas de promotion automatique |

*2026 déjà partiellement examinée : test chronologique, pas nouveau test indépendant vierge. Les lignes sur des périodes différentes ne sont pas un classement direct.

## Architecture, périodes, calibration et décisions

V1–V7 et Classic sont des régressions logistiques conditionnelles régularisées, probabilités softmax par course. Elo est une variable de V3 et suivants, pas un moteur Elo autonome validé. Les cotes opérateur ne sont pas utilisées en entrée.
V1 : 2024 entraînement, 2025 sélection, 5 octobre 2026 test, petits échantillons. V2/V3/V4 : mars 2024 entraînement, mars 2025 validation, mars 2026 test V2 et avril 2026 test V3. V4 n'est pas retenu : LL de validation combined 2,42461 contre 2,42387 pour V3.
V5–V7 : entraînement 2 mars–31 mai 2024 (1 563), validation mêmes mois 2025 (1 611). V5 : test mai–juin 2026. V6 : juillet–août 2025. V7 : septembre–octobre 2025. V6 améliore V5 sur le test apparié : LL 2,13935 contre 2,15205. Intervalle descriptif du gain V7 incluant zéro : [-0,01445 ; +0,00909].
Classic full : entraînement 2 mars 2022–31 décembre 2024 ; validation 2025 (6 398) ; test janvier–septembre 2026. Novembre 2024 exclu selon le protocole gelé ; course Vichy 2026-07-04_R6C7 exclue pour identités contradictoires. Les nouvelles archives ne changent pas ces exclusions ni les coefficients.
V6 : audit calibration 2 175 courses, ECE tous partants 0,43 point ; premier choix 1,43 point. Surconfiance possible dans certaines tranches élevées ; pas de recalibration réalisée. Classic full : température gelée sélectionnée en 2025, ECE test 0,579 point. Aucun modèle n'a démontré une rentabilité sur cotes observées.
Décision du 14 octobre : XGBoost et mélanges écartés. L'expérimentation ultérieure full history existe réellement et doit être inventoriée, mais ne renverse pas automatiquement cette décision. V6 reste principal ; V5 et V7 exécutés pour comparaison ; Classic full comparateur supplémentaire, pas « V8 » inventée.

## Fichiers exécutables et variantes

Point unique : `scripts/predict_operational.py --date YYYY-MM-DD --reunion R --course C`.
V5/V6 réutilisent `scripts/shadow_v6.py` et la vérification `scripts/v6_holdout.py` ; V7 réutilise `scripts/shadow_v7.py`. Modèles : `connections_v5_candidates.json` (combined), `demographics_tandem_v6_candidates.json` (combined), `speed_v7_candidates.json` (v7_speed). Locks : `connections_v5_frozen.json`, `v6_holdout_frozen.json`, `speed_v7_frozen.json`. Fonctions caractéristiques d'origine conservées, empreintes vérifiées.
Classic : `models/full_history/classic.json`, `frozen.json`, `config/full_history_protocol.json`, `turf_lab/full_history_features.prepare` ; température du lock appliquée.
Inventaire exhaustif des fichiers, SHA-256, variantes et noms des variables disponibles : `reports/operational/model_files.json`. Les variantes driver/trainer/equipment de V5, age_sex/tandem de V6, departure/aptitude de V4 et opposition/dq de V3 sont entraînées pour ablation, pas promues comme nouveaux modèles principaux. Les sources des métriques restent les rapports BACKTEST_*, CONNECTIONS_*, V6_HOLDOUT, V7_HOLDOUT et full_history/comparison.json.

## Simple placé

Méthode existante : Plackett–Luce top-3 à partir de Classic full, puis calibration logistique gelée sur les seuls premiers choix en 2025. Test exploratoire 2026 : 3 015 courses, fréquence placée 49,05 %, moyenne calibrée 49,81 %, Brier binaire 0,24491. Ce Brier binaire n'est pas comparable au Brier multiclasses gagnant.
Périmètre strict : seul premier choix Classic, 10–20 partants, zéro NP. Ne pas étendre aux autres chevaux ni à V5/V6/V7 sans validation. Confirmer trois places payées chez l'opérateur. Sans rapport probable pré-course documenté : « EV placé non calculable ». Aucun rapport définitif utilisé comme prix pré-course.
