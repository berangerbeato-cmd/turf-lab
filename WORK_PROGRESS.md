# TURF LAB — point de reprise Work V3

Mise à jour : 13 octobre 2026. Branche `main`.
Contraintes : gratuit, cloud uniquement ; aucun pari réel, achat, scraper de cotes,
MySQL, AspiTurf, VPN ou contournement. Cotes futures par capture manuelle.

## Phase actuelle

Reprise du 13 octobre : neuf tâches mensuelles réussies ; backtest bloqué avant entraînement par 18 courses annulées comptées comme résultats manquants en janvier 2026. Correctif testé (44 tests), audit `reports/cancellation_audit.json`, explication `reports/COVERAGE_CORRECTION.md`. Prochaine action immédiate : publier ce correctif puis reproduire le backtest figé.

Extension historique V2 : janvier 2024 entièrement collecté et sauvegardé (512 courses, 6 757 participations, 18 hippodromes). La chaîne mensuelle et les historiques strictement antérieurs sont reproduits dans GitHub Actions. Collecte bornée des premiers trimestres 2024, 2025 et 2026 lancée dans GitHub Actions ; nouveau protocole chronologique figé avant consultation du test. Le pilote prospectif V1 reste inchangé et **NO BET**.

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

1. Vérifier le workflow `history_extension.yml` (neuf mois, un seul collecteur à la fois). Ne pas attendre le suivi prospectif pour développer.
2. Lire `reports/month_YYYY-MM.json` et les manifestes dans `data/month_YYYY-MM/`. Si une tâche est interrompue, reprendre depuis les bruts sauvegardés et ne pas répéter les requêtes déjà enregistrées. Les programmes absents et quarantaines ne sont jamais convertis en zéros silencieux.
3. Le backtest V2 suit automatiquement la collecte seulement si les contrôles passent : calendriers complets, couverture >= 98 % par mois, >= 200 courses par partition, identités et empreintes valides. Blocage documenté dans `reports/history_extension_status.json` sinon.
4. Protocole V2 : janvier–février construisent les historiques ; 2–31 mars 2024 entraînement, 2025 validation, 2026 test inédit. Fenêtre antérieure de 60 jours, cinq courses maximum. Ne jamais régler sur le test ; ne pas remplacer le modèle prospectif V1 automatiquement.
5. Contrôler le futur `reports/BACKTEST_EXTENSION_V2.md`, les sous-groupes/calibration JSON et les sauvegardes. Aucun résultat V2 n'est encore annoncé à ce checkpoint.
6. Le suivi prospectif du 13 au 26 octobre continue indépendamment ; résultats jusqu'au 28. Aucun pari réel, ROI ou cote collectée automatiquement.

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
  Correctif publié et vérifié ci-dessous. Aucun force push.

## État final vérifié de cette session

- Audit corrigé : run `38286836315`, **success**, sauvegarde réussie.
- Pilote chronologique : run `38286899576`, **success**, résultats reproduits.
- Archives : run `38286899636`, **success**, empreintes contrôlées sans retéléchargement.
- Suivi prospectif corrigé : run `38287036836`, **success**, commit de sauvegarde
  `9a74bf7`. Modèle figé et deux courses distinctes capturées avant départ.
- Prédiction future : run `38285892128`, **success** ; JSON et HTML dans predictions/.
- 27 tests réussis. Aucun test final réutilisé pour régler le modèle.
- Reprise après incident vérifiée sur le conflit réel de sauvegarde ; checkout
  de main après acquisition du créneau d’écriture, SHA exécuté enregistré.
- Aucun backfill massif, aucune donnée de cotes réelle, aucun pari et aucun ROI.
- Limites : 40 courses historiques exploitables, six quarantaines, un seul jour
  de test historique ; le modèle reste expérimental. La fenêtre prospective
  doit produire de nouvelles preuves, pas une validation supposée d'avance.
- Tous les scripts, preuves, données normalisées, modèles, rapports et workflows
  sont publiés sur main. Le paquet ZIP initial est seulement un secours ancien.

## Extension mensuelle en cours — 13 octobre, heure de Paris

- Collecteur publié : `158098cc80ada5da883716406db06e7255a30e76`.
- Run `38313938501` observé en cours dans GitHub Actions ; succès pas encore établi.
- Construction des historiques strictement antérieurs écrite et testée ; workflow après collecte réussie.
- NO BET inchangé ; pas de réentraînement. Protocole : reports/MONTH_EXTENSION_PROTOCOL.md.
- Prochaine action : vérifier le run mensuel et sa sauvegarde, puis month_features et son rapport de couverture historique ; traiter les lacunes avant extension.

## Résultats mensuels vérifiés et nouvelle extension

- 512/512 courses de janvier 2024 contrôlées, 31/31 programmes, 1 055 réponses HTTP 200 ; 142 courses Vincennes, 370 province, 18 hippodromes.
- 6 568 participations actives ; 2 184 avec historique antérieur dans le mois (33,25 %). Un mois ne fournit pas des carrières complètes.
- Runs mensuels `38313938501`, `38315157655` et historiques `38315576125`, `38315622039` : succès. Bruts, rapports et données dans Git.
- Reprise depuis cache réellement vérifiée : zéro nouvel appel PMU. Commits hebdomadaires réels puis sauvegarde finale ; dernier état vérifié `6742c97`.
- 42 tests locaux réussis : couverture, quarantaine, sauvegardes hebdomadaires, identité, NP/DQ, absence de fuite cible/même jour/futur, fenêtre 60 jours, partitionnement et gel du backtest.
- Rapport de décision : `reports/JANUARY_2024_FEASIBILITY.md`. Protocole figé : `config/history_extension_protocol.json`.
- Nouveau backtest écrit et testé sur données synthétiques ; pas encore évalué sur les neuf mois réels. Modèle prospectif inchangé.

## Lancement V2 confirmé

- Commit de développement : `b5fea4f274eb8e3854ba3b6a2a02cdafdc6064d5`.
- Run actif : https://github.com/berangerbeato-cmd/turf-lab/actions/runs/38317253515 .
- Première tâche `collect (2024-01)` : succès, tests et sauvegarde confirmés ; tâche février 2024 créée ensuite.
- Les huit mois supplémentaires et le backtest ne sont pas encore terminés à ce checkpoint. La chaîne GitHub poursuit réellement l'exécution après la session ; aucune collecte pluriannuelle continue ni performance V2 ne sont encore annoncées.
- Aucune intervention utilisateur nécessaire au lancement. En cas d'échec d'un mois, conserver les checkpoints et reprendre la tâche concernée ; ne pas réinitialiser les historiques.

## Extension future demandée — position de départ (13 octobre 2026)

Statut : planifiée, non implémentée et non utilisée dans le modèle actuel.

- Auditer les champs avant-course disponibles dans les bruts existants : type de départ, position autostart, ligne, emplacement intérieur/extérieur, distance individuelle et échelon de recul.
- Autostart : distinguer première/deuxième ligne et position réelle ; vérifier les règles de correspondance par hippodrome avant toute dérivation. Ne pas assimiler automatiquement numéro du cheval et position de départ.
- Départ volté : représenter le recul en mètres (notamment 25/50 m) et l'échelon ; ne pas inventer de place fixe à partir du numéro.
- Étudier les interactions avec hippodrome, distance et nombre de partants ; aucune pénalité universelle fixée arbitrairement.
- Mesurer couverture et ambiguïtés ; conserver les valeurs inconnues, leur provenance et la preuve de disponibilité avant départ. Absence d'autostart ne signifie pas départ volté.
- Comparer avec/sans ces variables sur validation chronologique (log loss, Brier, calibration et sous-groupes). Sélectionner sur validation uniquement ; réserver un test indépendant si le test V2 a déjà été consulté.
- Conserver le protocole V2 en cours et le modèle prospectif V1 figés. Intégration effective seulement après audit, implémentation et évaluation documentés.
- Prochaine action pour cette extension : inventorier les champs de départ dans les données mensuelles sauvegardées et établir leur taux de disponibilité.

## Extensions futures demandées — météo et terrain (13 octobre 2026)

Statut : planifiées ; disponibilité des sources à auditer, non intégrées au modèle actuel.

- Terrain/piste : distinguer revêtement, configuration du parcours et état de piste annoncé (humidité, piste lourde ou autres libellés réellement fournis). Conserver le libellé source et sa signification propre au trot ; ne pas transposer automatiquement une échelle du galop.
- Météo : rechercher une source gratuite autorisée donnant température, pluie récente/cumulée, vent (vitesse et direction), et si utile humidité, avec localisation de l'hippodrome, distance de station et horodatage.
- Séparer observations disponibles avant départ, prévisions émises avant départ et mesures constatées après. Une archive météo réalisée ou réanalysée ne doit pas être présentée comme une prévision historique disponible à l'époque.
- Ne jamais utiliser le cumul de pluie de toute la journée pour une course antérieure à la fin de cette journée. Ne pas déduire un état de piste certain de la seule météo ; entretien et drainage restent des facteurs non observés.
- Mesurer la couverture historique et prospective, les délais de publication et les valeurs manquantes avant intégration ; aucune donnée manquante remplacée silencieusement par « sec ».
- Étudier les interactions avec revêtement, hippodrome, distance et performances antérieures du cheval dans des conditions comparables ; réduire les ajustements quand l'historique est faible.
- Comparer les ajouts météo et terrain séparément puis ensemble sur validation chronologique, avec log loss, Brier et calibration. Conserver uniquement les gains mesurés ; test indépendant non utilisé pour régler les variables.
- Prochaine action : inventorier les champs piste/terrain dans les bruts PMU sauvegardés, puis identifier une source météo gratuite seulement si ces données manquent. Préserver le protocole V2 en cours et le modèle prospectif V1 figés.

## Trois axes prédictifs futurs — demande confirmée le 13 octobre 2026

Statut : planifiés, non implémentés ; ne pas les confondre avec les cinq variables du pilote actuel.

1. **Niveau de l'opposition** : construire une note évolutive de type Elo adaptée aux courses à plusieurs partants, en utilisant uniquement les résultats antérieurs. Comparer chaque cheval au lot du jour avec les notes disponibles avant départ. Définir et valider le traitement des DQ, NP, égalités et rangs inconnus ; séparer autant que possible capacité et faute. Initialisation prudente des nouveaux chevaux et mises à jour après course seulement.
2. **Risque de faute/disqualification** : référence par fréquence historique régularisée vers une moyenne estimée sur l'entraînement, puis modèle contextuel si les données le permettent (repos, départ, driver, etc.). Distinguer probabilité de DQ et capacité conditionnelle à la non-DQ. La factorisation P(victoire)=P(non-DQ)*P(victoire|non-DQ) est une relation théorique, pas une implémentation suffisante : assurer cohérence au niveau de la course et calibration. Mesurer séparément qualité du modèle de DQ et apport au modèle de victoire.
3. **Adéquation au départ et au parcours** : estimer les écarts de performance au niveau habituel selon distance, hippodrome, type de départ, position/ligne autostart et recul. Tenir compte de l'opposition pour ne pas confondre parcours favorable et lot faible. Régulariser fortement les petits historiques et utiliser des effets collectifs quand les observations individuelles manquent. Articuler avec les extensions départ, météo et terrain décrites ci-dessus.

Protocole commun : auditer les champs et la profondeur historique, construire les variables strictement avant chaque cible, comparer chaque bloc seul puis leur combinaison à la référence sur validation chronologique. Apprendre hyperparamètres et régularisation sans consulter le test final. Si le test V2 a déjà été consulté, prévoir un autre test indépendant pour les nouveaux choix. Ne retenir une complexité supplémentaire que si elle améliore les résultats mesurés (log loss, Brier, calibration). Aucun remplacement du modèle prospectif figé ni changement du protocole V2 en cours.

Prochaine action pour ces axes : après contrôle de l'extension historique, établir couverture et protocole expérimental ; commencer par la note d'opposition et une référence DQ régularisée.

<!-- CLOUD_CHECKPOINT -->
## Dernière exécution Actions observée automatiquement

- Horodatage UTC : 2026-10-13T05:52:05.244984+00:00.
- Run : https://github.com/berangerbeato-cmd/turf-lab/actions/runs/38353059579
- Commit déclencheur : `c2186c98c5a02306d792f7ae91f18384b9c63a90`.
- Commit réellement extrait et exécuté : `d448f1d739a15a30941fc7bd176c00d8ba158298`.
- Statut avant sauvegarde : **success**.
- La sauvegarde Git se fait à l'étape suivante ; confirmer son résultat dans le run.
- Une exécution d'audit réussie ne valide pas un modèle prédictif.
- En cas d'échec, les rapports précédents peuvent être périmés ; utiliser le journal
  et les manifestes pour reprendre au premier appel absent, sans répéter les autres.
