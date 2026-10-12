# TURF LAB — point de reprise Work V3

Mise à jour : 12 octobre 2026. Branche `main`.
Contraintes : gratuit, cloud uniquement ; aucun pari réel, achat, scraper de cotes,
MySQL, AspiTurf, VPN ou contournement. Cotes futures par capture manuelle.

## Phase actuelle

Phase A terminée. Stockage Git durable opérationnel. Pilote B/C/D exécuté dans
le runtime cloud : 40 courses exploitables sur 46 candidates, six quarantaines
explicites. Régression expérimentale ; pas de modèle validé, **NO BET**.
Prédictions prospectives et rapports mobiles générés. Workflows pilote et
prédiction réussis sur GitHub Actions. Observation quotidienne bornée en préparation.

## Travaux publiés et vérifiés

- Commit `6f46485c2c9221522790535d27d936e4dd77a29e` : 171 fichiers transférés,
  code/audit/rapports et 126 réponses brutes avec empreintes.
- Run audit `38284344664` : succès ; tests et reproduction sur GitHub Actions.
- Run récupération `38284344661` : succès ; les ZIP de référence sont désormais
  dans `data/reference`, sauvegardés par le commit distant `e8bd4a6`.
- ZIP pmu-deep-audit : 14 courses, 203 participants, 42 requêtes, recomptés.
- ZIP pmu-probe : 149 fichiers participants dans raw/. Les 10 copies présentes
  dans results_probe/ ne sont pas des courses supplémentaires.
- Les deux SHA-256 des archives correspondent aux métadonnées Actions.
- Le connecteur GitHub fonctionne en écriture. Les anciennes erreurs ont cessé.
  Le navigateur a expiré ; il n'est plus nécessaire. Autorisation utilisateur
  acquise, ne pas la redemander.

## Résultats d'audit

- 149 courses sur sept jours = 99 françaises + 50 étrangères ; filtre pays corrigé.
- 46 courses françaises, 619 participants, 12 hippodromes : 16 courses 2024,
  16 de 2025 et 14 du 05/10/2026. 46 gagnants uniques concordants.
- 15 non-partants, 124 disqualifiés/distancés, 2 arrêtés, 6 rangs inexpliqués.
  Garder les rangs manquants ; cible victoire contrôlée séparément.
- Cinq historiques : FABIUS ORS 3, LORD ON WAY 10, OVER THE HILL 2,
  GISARO 10, MAZURKA DE BELI 10 courses antérieures retenues.
- idCheval absent sur 327 lignes : composite nom-mère-père contrôlé.
- pretty : jusqu'à cinq performances antérieures ; publication originelle non prouvée.
- Ferrure absente ≠ ferré ; autostart absent ≠ volté ; timeRecord ≠ record personnel.
- Rapports détaillés : reports/AUDIT_FEASIBILITY.md et FIVE_HORSE_HISTORIES.md.

## Tests et code

- 17 tests d'audit/EV publiés et exécutés dans Actions.
- 6 tests pilote supplémentaires passent dans le runtime cloud (23 au total) :
  fuite cible/futur, probabilités/NP, indépendance des cotes, DQ, métriques.
- scripts/reconcile_reference.py exécuté avec succès après correction du
  comptage des copies results_probe/. Rapports de rapprochement sauvegardés.
- config/pilot_protocol.json : train 2024, validation 2025, test 05/10/2026.
  Uniforme et régression conditionnelle avec deux pénalisations prédéfinies.
  Sélection sur validation seulement ; aucun réglage à partir du test.
- scripts/build_pilot.py : exactement 46 courses ; réemploi des quatre captures
  pretty déjà validées, 42 appels initiaux et 5 nouvelles tentatives bornées. Collecte terminée avec quarantaines explicites.
- turf_lab/pilot.py et scripts/backtest_pilot.py : écrits et exécutés sur le sous-ensemble contrôlé. Toujours statut expérimental/NO BET.

## Résultats supplémentaires vérifiés

- 37 nouvelles réponses pretty réussies, 5 réponses vides après une unique
  nouvelle tentative chacune ; une course mise en quarantaine pour deux lignes
  sans itsHim (KINASSE DE VIVOIN et FUNNY GIRL (ITY), historique du 27/06/2025).
- Quarantaine définie sur la qualité des données avant le premier backtest :
  46 candidates, 40 retenues. Aucun résultat inventé ni sélection selon performance.
- Train 14 courses en 2024 ; validation 12 en 2025 ; test 14 du 05/10/2026.
- Sélection validation : régression conditionnelle. Test : log loss 2,484502
  contre 2,644439 uniforme ; Brier multiclasses 0,896022 contre 0,928181 ;
  top-1 1/14 pour les deux. Aucun ajustement après observation du test.
- Calibration, sous-groupes et ablations validation enregistrés dans
  reports/backtest_pilot_v1.json. Petit échantillon, test sur une seule journée,
  couverture non représentative : aucune conclusion de rentabilité/fiabilité.
- Modèle sérialisé models/pilot_v1.json ; partitions JSONL.gz et empreintes
  data/pilot_v1/manifest.json ; bruts evidence/pilot_v1 conservés dans Git.
- Première prédiction réelle avant-course : 2026-10-13 R4C1 Vincennes, 12 partants,
  somme des probabilités 1,0, historique strictement antérieur ; rapport HTML mobile.
- Intégration EV sur cotes synthétiques : NO BET confirmé. Aucune capture réelle
  reçue. Le modèle expérimental ne peut produire de candidat de mise.
- Syntaxe Python et YAML contrôlée. 27 tests passent ; contrôles de normalisation,
  chronologie et raccordement EV sur la prédiction enregistrés séparément.

## Prochaine action précise

1. Publier puis vérifier le workflow daily_shadow et son premier run ;
   inscrire son identifiant et le résultat de sauvegarde dans ce checkpoint.
2. Le suivi collecte au maximum deux courses par jour, une à Vincennes et une
   en province, pour les départs du 13 au 26 octobre. Le contrôle des résultats
   se poursuit jusqu’au 28 octobre puis les appels PMU cessent. Ne pas élargir
   cette fenêtre ni changer le modèle sans versionner un nouveau protocole.
3. Suite scientifique : préparer une extension bornée et un nouveau protocole
   figé avec davantage de jours/hippodromes ; ne pas réutiliser le test V1 pour
   sélectionner des améliorations. Préférer des captures prospectives horodatées.
4. Lors d'une capture utilisateur, refaire les partants et probabilités avant
   lecture des cotes, vérifier identités/heure/convention, calculer EV ; maintenir
   NO BET tant que validation prospective insuffisante. Aucun pari réel.

## Reprise

Lire ce fichier puis les derniers commits/runs. Réutiliser les bruts, contrôler
les empreintes ; ne pas refaire les étapes validées. La sauvegarde de secours
Turf_Lab_Reprise_2026-10-12.zip contient l'état d'audit antérieur à la publication.
Les commits locaux originaux sont aussi conservés sous recovery/local-audit-4f72b50.

## Déploiement du pilote confirmé

- Commit publié `a1e4517d5f83071ccaa34a6d1257e28705f69e00`.
- Run pilote `38285892122` : succès, résultats reproduits et sauvegardés.
- Run prédiction `38285892128` : succès, nouvelle capture avant-course sauvegardée
  par le commit `0594c2d`. Deux captures de Vincennes existent ; utiliser la plus
  récente avant départ, sans effacer l’ancienne.
- Prédiction Lyon-Parilly du 13/10 R3C1 exécutée ensuite dans le runtime cloud,
  rapport et preuves conservés. Deux courses distinctes prospectives disponibles.
- Suivi prospectif exécuté localement : zéro course évaluée (départs demain),
  aucune métrique prospective ni résultat inventé.
- Quatre tests supplémentaires de notation prospective réussis : 27 tests total.
  Résultat provisoire, arrivée ambiguë, pronostic tardif ou partants modifiés
  ne sont jamais évalués comme s’ils étaient valides.
- Modèle figé par SHA-256 dans config/shadow_protocol.json. Aucun réentraînement
  automatique, aucune promotion vers un statut de pari.

## Suivi prospectif et correctif de sauvegarde

- Run prospectif `38286546386` : succès, commit de sauvegarde `e00ac24`.
  Planification quotidienne à 06:15 UTC, modèle figé, fenêtre bornée ci-dessus.
- Run audit `38286546493` : calculs et 27 tests réussis, mais sauvegarde échouée
  sur conflit WORK_PROGRESS.md (rebase depuis le SHA déclencheur ancien).
  Les données étaient déjà conservées dans Git ; l’artefact diagnostic existe.
- Correctif : checkout explicite de main à l’entrée de chaque workflow écrivain
  sérialisé ; journal séparant SHA déclencheur et SHA réellement exécuté.
  Publication et vérification du correctif en cours. Aucun force push.

<!-- CLOUD_CHECKPOINT -->
## Dernière exécution Actions observée automatiquement

- Horodatage UTC : 2026-10-12T17:50:43.005442+00:00.
- Run : https://github.com/berangerbeato-cmd/turf-lab/actions/runs/38286899576
- Commit déclencheur : `8ded7dc3ec8a802305ad1cdb33ad99b402da8fcb`.
- Commit réellement extrait et exécuté : `8ded7dc3ec8a802305ad1cdb33ad99b402da8fcb`.
- Statut avant sauvegarde : **success**.
- La sauvegarde Git se fait à l'étape suivante ; confirmer son résultat dans le run.
- Une exécution d'audit réussie ne valide pas un modèle prédictif.
- En cas d'échec, les rapports précédents peuvent être périmés ; utiliser le journal
  et les manifestes pour reprendre au premier appel absent, sans répéter les autres.
