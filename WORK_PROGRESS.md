# TURF LAB — point de reprise Work V3

Mise à jour : 12 octobre 2026. Branche visée : `main`.
Contraintes : zéro achat/abonnement/API payante ; cloud uniquement ; aucun pari
réel, scraper de cotes, MySQL, AspiTurf, VPN ou contournement.

## Phase actuelle

**Phase A réalisée sur un échantillon borné. Rapport de faisabilité disponible.**
GO conditionnel pour un pilote ; pas de collecte massive ni base définitive.
Phase B proposée, pas déployée. Modèle/backtest non commencés.
L'écriture GitHub bloque la publication ; le code et les données doivent être
sauvegardés dans un paquet de reprise avant la fin de session.

## Dépôt distant : faits vérifiés

- État initial `d69d555806b40be9b61c025d201fd43ffbfaf7b6`, dépôt public,
  droits push annoncés par le connecteur.
- Run de référence `38238010891`, job `114773373147` : succès confirmé.
- Artefact `11741548220`, `pmu-deep-audit`, 115580 octets, SHA-256
  `b2fac86c0419d6a83b0323a18e49126762e059fa4da1b8b76bdcc9116053739e`.
- Run `38233770270` réussi ; artefact `11740330993`, `pmu-probe`, 849323 octets,
  SHA-256 `057bfef8fc6cc45d5bef921af696c5097bbfbc714c0de596c669a980f659e3f2`.
- Ces ZIP sont identifiés mais **pas récupérés**. La récupération prévue dans
  `scripts/recover_reference.py` n'est pas encore exécutée.
- `get_repo`, `get_user_login` et lecture GitHub par `fetch` fonctionnent.
- `fetch_file`, `download_workflow_artifact`, `create_tree`, `create_file` et
  certains outils de jobs échouent : `InvalidActionArgumentsError`, validation
  des arguments. Ne pas boucler sur ces appels inchangés.
- `git clone`/lecture publics réussis. `git push origin main` échoue :
  `could not read Username for https://github.com` (pas d'authentification Git).
- **Aucun commit nouveau ni workflow nouveau confirmé sur GitHub.**

## Résultats vérifiés, pas des promesses

- Programmes 05–11/10/2026 : **149 attelés, dont 99 FRA et 50 étrangers**.
  Les collecteurs d'origine omettaient le filtre pays, corrigé dans cette reprise.
- Audit principal : **46 courses, 619 participants, 12 hippodromes**.
  2024 : 16 courses / 218 participants ; 2025 : 16 / 198 ; 05/10/2026 : 14 / 203.
  Huit dates historiques, 107 réponses HTTP 200 sur le collecteur principal.
- Gagnants concordants entre participants et détails pour 46/46 courses.
  15 non-partants, 124 disqualifiés/distancés (dont 4 DISTANCE), 2 arrêtés,
  6 partants sans rang ni incident explicatif : ne pas inventer leurs rangs.
- 327 identités composites reconstruites (nom-mère-père) faute d'idCheval direct.
- Cinq chevaux, avant le 05/10/2026 : FABIUS ORS 3 courses, LORD ON WAY 10,
  OVER THE HILL 2, GISARO 10, MAZURKA DE BELI 10. Historiques limités explicités.
- Source officielle découverte et testée : `program/{id}/light-performances`.
  Le JSON contient aussi la course cible et des courses ultérieures : filtre
  strict `raceDate < targetDate`, pas de résumé de carrière contemporain.
- Ancien endpoint `performances-detaillees/pretty` : 297 lignes de performances
  sur quatre courses 2024/2025 ; aucune à la date cible ou après. Jusqu'à cinq
  performances par cheval ; peut montrer seulement le top-5 + le cheval.
- `performance-details` testé sur LORD ON WAY à La Capelle le 21/09/2026 :
  les 15 participants sont retournés, avec l'opposition et les résultats.
- Deux captures avant course pour le 13/10/2026, Lyon-Parilly/Vincennes,
  28 partants, pas d'arrivée/chrono/commentaire après-course.
- Gains en centimes : conversion /100 vérifiée dans le client officiel PMU.
  Chronos participants en ms : cohérence vérifiée sur 467 lignes, erreur
  médiane 0,0625 s / maximum 0,14 s avec réduction × distance.
- Ferrure manquante ≠ ferré ; absence d'autostart ≠ preuve de départ volté.
  `timeRecord` est une durée de course, pas un record de carrière validé.

## Code écrit et exécuté dans le runtime cloud

- Cache d'évidence borné, JSON.gz exacts, UTC/URL/SHA-256, écriture atomique,
  reprise sur fichiers existants, vérification d'intégrité sans réseau au replay.
- Scripts audit_phase_a, audit_horses, audit_temporal, audit_before_race,
  audit_opposition et build_audit_report : exécutés avec résultats conservés.
- Modules history/quality et filtre pays, 17 tests réussis dans
  `reports/test_results.txt` : fuite temporelle, non-partants, disqualifications,
  DISTANCE, identités, cache intègre, retrait du jeton GitHub en redirection,
  EV indépendante, correspondances, heure, format de cote et NO BET.
- Comparateur manuel EV : testé sur fixtures seulement. Pas de lecture de capture
  réelle ni de modèle branché. Un modèle expérimental impose NO BET.
- Workflows recovery et phase_a : code préparé, **pas d'exécution GHA confirmée**.

## Commits locaux et fichiers

- `0364253` : initialisation du checkpoint et récupération des preuves préparée.
- `edd8747` : collecteur d'audit borné et découverte des endpoints.
- `cdbed01` : audits, preuves, rapports, 17 tests et correctifs.
- Vérification finale : 126 corps JSON.gz relus, empreintes exactes, Python
  compilé et syntaxe des quatre workflows YAML vérifiée.
- Le paquet de reprise comporte un patch binaire complet contre le SHA initial,
  les rapports et ce fichier. Son intégrité de restauration est testée avant remise.
- Rapports : `reports/AUDIT_FEASIBILITY.md`, `FIVE_HORSE_HISTORIES.md`, JSONs
  d'audit/qualité/variables/décision. Proposition : `docs/ARCHITECTURE_PROPOSAL.md`.
- Les réponses brutes sont dans `evidence/`. Ne pas refaire leur collecte :
  rejouer les scripts valide les empreintes et réutilise les captures.

## Prochaine action précise

1. Rétablir une voie d'écriture GitHub. Le recours au navigateur après l'échec
   répété du connecteur nécessite l'accord explicite de l'utilisateur selon
   les instructions du navigateur. Ne pas réclamer un secret dans le chat.
2. Publier le paquet préparé sur main après vérification du HEAD distant ; si
   main a changé, intégrer les changements sans force push ni écrasement.
3. Vérifier les deux nouveaux workflows, leurs commits de sauvegarde et les ZIP
   de référence. Mettre à jour ce fichier avec les vrais SHA et run_id.
4. Puis Phase B : petit lot durable versionné, identités et dates de publication,
   données normalisées et contrôle qualité. Résoudre les 6 rangs non expliqués
   avant un modèle nécessitant un classement complet ; conserver des manquants
   pour ferrures, volté, piste/terrain et records non prouvés.
5. Pilote historique limité, périodes train/validation/test figées, baseline
   uniforme puis modèle explicable sans cotes. Aucun ROI sans cotes réellement
   capturées avant départ. La taille de cet audit ne suffit pas à valider un modèle.
6. Prédictions futures, recalcul non-partants, transcription manuelle des captures
   et restitution iPhone après validation du modèle.

## Reprise après interruption

Lire ce fichier, les derniers commits et workflows. Si seul le paquet de reprise
est disponible, suivre RESTORE.md. Contrôler d'abord l'état réel de GitHub.
Ne pas recréer des rapports déjà présents, ne pas répéter la collecte validée.
Ne pas confondre fichiers écrits, tests hors ligne réussis et workflow opérationnel.
