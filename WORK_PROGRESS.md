# TURF LAB — point de reprise Work V3

Mise à jour : 12 octobre 2026. Branche `main`.
Contraintes : gratuit, cloud uniquement ; aucun pari réel, achat, scraper de cotes,
MySQL, AspiTurf, VPN ou contournement. Cotes futures par capture manuelle.

## Phase actuelle

Phase A terminée sur échantillon borné : GO conditionnel pour petit pilote.
Phase B : stockage Git durable opérationnel pour les preuves d'audit ;
normalisation du pilote en cours. Phase C/D : code expérimental en préparation,
aucun résultat prédictif annoncé à ce checkpoint. Pas de collecte massive.

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
  pretty déjà validées, au maximum 42 nouvelles requêtes. Collecte en cours.
- turf_lab/pilot.py et scripts/backtest_pilot.py : écrits ; backtest complet
  pas encore exécuté à ce checkpoint. Toujours statut expérimental/NO BET.

## Prochaine action précise

1. Terminer build_pilot ; examiner les erreurs plutôt que réduire silencieusement
   l'échantillon. Vérifier les identités et les dates des historiques.
2. Exécuter backtest_pilot, sauvegarder les données normalisées JSONL.gz,
   manifestes et résultats ; publier le workflow puis confirmer son succès.
3. Construire et tester la prédiction future et le rapport iPhone ; conserver
   NO BET tant que validation insuffisante. Brancher le contrat de captures
   manuelles déjà testé ; aucun historique de cotes/ROI inventé.
4. Collecte prospective et extension bornée décidée selon les limites mesurées.
   Pas d'arbres/Elo supplémentaires sans bénéfice démontré et volume suffisant.

## Reprise

Lire ce fichier puis les derniers commits/runs. Réutiliser les bruts, contrôler
les empreintes ; ne pas refaire les étapes validées. La sauvegarde de secours
Turf_Lab_Reprise_2026-10-12.zip contient l'état d'audit antérieur à la publication.
Les commits locaux originaux sont aussi conservés sous recovery/local-audit-4f72b50.
