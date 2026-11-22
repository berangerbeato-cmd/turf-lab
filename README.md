# TURF LAB V4 : TOUTES LES AMÉLIORATIONS SONT ACTIVES (22 novembre 2026)

**Une seule version utilisateur : TURF LAB V4, moteur `turf_lab_v4_fully_integrated_1`, toujours 47 caractéristiques.** Le gagnant utilise maintenant réellement les 47 variables, la **température contextuelle hippodrome/départ/distance** et le **résiduel signé de risque de disqualification** calibré. Le poids DQ est **0,020841862**, appris sur **3 156 courses de janvier à juin 2025**, et non fixé arbitrairement. History Repair V2 contrôle les sources, confirme les corrections admissibles et conserve les conflits en quarantaine.

**Value réelle du calcul modèle :** si une grille complète de cotes vérifiées est disponible avant la course, la V4 utilise désormais sa correction de marché conditionnelle à R, **puis applique la correction par tranche de cote** dans la probabilité gagnant et dans l'EV théorique affichée. Sans grille vérifiée, aucune value n'est inventée.

**Top 5 / Quinté :** la **meilleure combinaison sans ordre** selon le modèle joint à cinq positions est désormais **le Top 5 et le Quinté uniques affichés**, et non un résultat alternatif laissé en observation. La probabilité jointe estimée est affichée avec ses limites de calibration.

**Les cinq évolutions sont actives dans la sortie principale** :
- History Repair V2 : audit de qualité, résolution prudente, conflits non réécrits
- Disqualifications : poids résiduel appris et appliqué
- Hippodrome / distance / départ : correction appliquée à la probabilité gagnant
- Favoris / outsiders : biais par tranche de cotes appliqué au marché et à la value si cotes vérifiées
- Quinté : meilleure combinaison de probabilité jointe sans ordre, utilisée comme sélection unique

**L'entraînement est terminé et les calculs sont intégrés.** Ce n'est pas une validation de rentabilité : évaluations 2025/2026 réutilisées, attente des prochaines courses réellement enregistrées avant départ. `config/recommendation_policy.json` reste **SUSPENDED / NO BET**. Aucun ticket réel ni montant de mise n'est recommandé.

[Configuration V4 active](config/v4_active.json) | [Gel des paramètres appliqués](models/v4_active_activation/frozen_activation.json) | [Rapport calibrage DQ](reports/v4_active_activation/RESULTS.md) | [Suivi de 10 courses par jour](reports/v4_integrated/prospective_scores.json)

---

## Archives et explications antérieures

# Suivi prospectif V4 : objectif 10 courses par jour (22/11/2026)

**Collecte automatique programmée**, sans intervention ni pari : **jusqu'à 10 courses françaises de trot attelé par jour**. La sélection des dix premières courses admissibles est enregistrée et figée dès la première exécution du jour, au moins 40 minutes avant départ. Une course impossible ou manquée reste visible comme échec : elle n'est jamais remplacée par une course choisie a posteriori.

**Six déclenchements par jour**, à 06 h 10, 08 h 10, 10 h 10, 12 h 10, 14 h 10 et 16 h 10 (Europe/Paris). Maximum **4 courses par exécution**, maximum **10 courses planifiées par jour**. Les appels PMU et les résultats officiels restent soumis à disponibilité : 10 est un objectif de collecte, **pas une garantie de 10 résultats vérifiés quotidiennement**.

Le suivi écrit `reports/history_repair_shadow_v1/prospective_forecasts/<jour>/selection_plan.json`, `daily_summary.json` et `reports/v4_integrated/prospective_scores.json` pour mesurer sélection, tentatives, captures réellement réussies, courses vérifiées et progrès vers les **200** évaluations prospectives. Une seule V4 47 caractéristiques, `NO BET` inchangé.

---

# TURF LAB V4 : les cinq derniers chantiers intégrés ensemble (22/11/2026)

**Toujours une seule V4.** Les 47 variables et trois modèles d'origine gagnant/Top5/cotes restent gelés. Son **même rapport** `v4_integrated.json` incorpore désormais, via le lot [V4 Next Bundle](reports/v4_next_bundle/RESULTS.md), cinq nouveaux contrôles :

1. **History Repair V2** : classer les écarts de profondeur des historiques, isoler les vrais conflits, ne jamais inventer des anciennes courses. 6 848 cas de fenêtre 60 jours contre historique plus profond, 103 conflits conservés en quarantaine.
2. **DQ** : modèle de risque entraîné sur 224 047 participants ; indicateur séparé du gagnant pour éviter d'appliquer une double pénalité.
3. **Hippodrome/départ/distance** : températures calibrées et régularisées sur les groupes suffisamment documentés.
4. **Tranches de cotes** : corrections exploratoires 1-4, 4-8, 8-20, 20-50, 50+, avec limitation de l'effet et tests historiques.
5. **Quinté sans ordre** : probabilité jointe calculée depuis le vrai modèle à cinq rangs conditionnels, sans produit abusif des probabilités individuelles.

**Bilan exploratoire 2026 (déjà connu, non indépendant) :** DQ Brier 0,16375 contre 0,17017 pour une référence constante ; contexte gagnant log loss 2,10285 → 2,10234 ; cotes PMU log loss 1,92332 → 1,91797 ; Quinté 6 réussites pour 5,31 attendues sur 246 courses. Il reste à vérifier ces gains sur des prévisions réellement archivées AVANT le départ.

**Aucune seconde V5/V6, aucun pari ni mise conseillés.** Le premier choix gagnant reste fondé sur les coefficients V4 47 variables gelés ; les nouveaux réglages par contexte/cote sont exposés en simulation tant que la validation prospective n'est pas acquise. La qualité des historiques, le risque DQ et le Z5 affichent leurs diagnostics dans le rapport unique.

[Résultats des cinq chantiers](reports/v4_next_bundle/RESULTS.md) | [Modèle V4 actif](config/v4_active.json) | [Suivi prospectif](reports/v4_integrated/prospective_scores.json) | [Audit GitHub](https://github.com/berangerbeato-cmd/turf-lab/actions/runs/44964541734)

---

## Ancien suivi conservé ci-dessous

# TURF LAB V4 : toutes les pistes intégrées en une fois (22 novembre 2026)

**UNE SEULE V4, 47 variables, poids réellement réentraînés :** les 43 variables précédentes (dont le chrono corrigé V7), les gains de carrière relatifs issus de la dernière course antérieure, la classe relative cumulée des résultats passés, la forme pondérée 35/25/18/12/10, et l'indice R de complétude des données. Le modèle de cotes apprend un coefficient de modulation selon R sur un sous-ensemble temporel distinct de 2025.

Le seul moteur public est `turf_lab/v4_multifeature_inference.py`, et le seul point d'entrée d'une course `scripts/run_prediction_request.py`. `config/v4_active.json` pointe vers `models/v4_multifeature/` ; ses **nouveaux** modèles gagnant / cinq positions / marché sont figés par empreintes SHA. Les sources V3 sont conservées **exactement gelées** et les entrées supplémentaires passent par `scripts/capture_v4_context.py`, hors du code V3.

**Test exploratoire 2026 déjà consulté :** log loss gagnant 2,107134 → 2,102854, top1 gagnant **27,08 % → 26,63 % (baisse)**, Top5 exact 109 → 111/4 574, cotes PMU log loss 1,924123 → 1,923323. **Ce n'est pas une validation indépendante, ni une preuve de rentabilité.**

Les montants de gains récupérés lors de courses antérieures sont des archives rétrospectives ; leur disponibilité historique au moment exact du départ ne peut être entièrement certifiée. Les valeurs non vérifiables restent manquantes. L'indice R mesure la complétude, **pas** une probabilité de gagner.

La validation des seules prochaines prévisions sauvegardées avant départ est dans `reports/v4_integrated/prospective_scores.json`. Les recommandations de mises restent suspendues (`NO BET`).

[Configuration de la V4 active](config/v4_active.json) | [Rapport complet](reports/v4_multifeature/RESULTS.md) | [Mode d'emploi](docs/V4_UNIQUE.md)

---

## Archives techniques antérieures

# Turf Lab V4 : chronos corrigés V7 INTÉGRÉS (22 novembre 2026)

**Un seul modèle actif pour les nouvelles analyses : TURF LAB V4, version `turf_lab_v4_integrated_speed_1`, avec 43 variables.**

La vitesse corrigée d'après les courses antérieures, héritée de V7, est désormais la **43e variable du vrai moteur V4**. Les trois nouveaux ensembles de poids `models/v4_speed/winner.json`, `models/v4_speed/ranking.json` et `models/v4_speed/market.json` sont utilisés par `turf_lab/v4_active_inference.py`. **Plus de modèle Speed parallèle à choisir**.

Le pré-traitement `History Repair V1.1` et la preuve originale `v4_speed_context.json` sont **obligatoires**, obtenus avant le départ dans `scripts.predict_operational` ou le collecteur planifié. Pas de repli silencieux sur les anciens 42 coefficients. Les chevaux sans chrono antérieur ont une valeur manquante prévue par l'entraînement, pas un chrono inventé.

**Comparaison exploratoire 2026, 4 661 courses gagnant** : log loss V4 précédente **2,11568** contre **2,10713** avec la 43e variable ; Top5 exact **103/4 574** contre **109/4 574** ; cotes PMU log loss **1,92499** contre **1,92412**. Ces données ont déjà été consultées, elles ne prouvent pas de gain indépendant ni de rentabilité. Surveillance originale pré-départ : `reports/v4_integrated/prospective_scores.json`.

**Les mises réelles restent suspendues** (`config/recommendation_policy.json`). Une V4 intégrée n'est pas une preuve d'EV fiable sur ZEturf.

[Mode d'emploi actuel](docs/V4_UNIQUE.md) | [Comparaison V4/Speed](reports/v4_speed/RESULTS.md) | [Modèle actif](config/v4_active.json).

---

## Historique de la V4 sans chrono (ancien état, conservé)

# Turf Lab V4 — modèle unique réentraîné (21 novembre 2026)

**Version visible pour les nouvelles courses : `turf_lab_v4_full_retrained_candidate_1`.**
Le moteur utilise une réconciliation obligatoire des historiques, un **nouveau modèle gagnant**, un **nouveau classement conditionnel Top 5** et une **nouvelle correction des cotes**. Les trois ensembles de poids ont réellement été entraînés sur des périodes chronologiques séparées. Les modèles V3/V2 restent seulement des archives de contrôle.

**Résultats vérifiés :** 17 532 courses gagnant, 17 335 courses pour le classement, 1 711 courses pour le marché ; 365 corrections historiques vérifiées sur 157 courses. Test 2026 déjà inspecté : gagnant log loss 2,11568 (V3 2,11586), Top5 exact 103/4 574 (référence 79/4 574), correction des cotes 1,92499 (ancienne 1,92489). Aucun gain de rentabilité démontré.

**Statut : V4 entraînée mais non validée prospectivement. Pas de paris réels ni de conseil de mise.** Les cotes restent d'origine PMU sur le test historique ; ZEturf est hors validation. Détails : [mode unique V4](docs/V4_UNIQUE.md), [résultats complets](reports/v4_full/RESULTS.md), [suivi d'entraînement](reports/v4_full/status.json), [protocole de suspension](config/recommendation_policy.json).

---

> **29 octobre 2026 — recommandations de paris suspendues.** L’audit face aux cotes
> confirme une sous-estimation des favoris et une surestimation des outsiders.
> Les calculs figés continuent uniquement pour la recherche, sans conseil de mise.
> Voir [résultats et limites](reports/value_audit_2026-10-29/RESULTS.md) et
> [politique de suspension](config/recommendation_policy.json).

# État opérationnel — reprise du 16 octobre 2026

Voir [audit complet](reports/OPERATIONAL_MODEL_AUDIT.md) et [mode opératoire](docs/OPERATIONAL_USAGE.md).
Le point unique est `scripts.predict_operational` : V6 principal et Classic full seul comparateur (V5/V7 archivés), aucun réentraînement. La collecte quotidienne et la prédiction utilisent désormais les mêmes archives réconciliées. Les captures de cotes sont traitées par ChatGPT, puis comparées aux sorties réelles. Les sections ci-dessous décrivent l'ancien pilote et sont conservées pour traçabilité ; elles ne donnent pas la taille actuelle de l'historique.

# Turf Lab

Laboratoire de recherche gratuit, cloud, consacré au **trot attelé en France**.
Aucun pari réel. Aucun abonnement, achat de crédit, API payante, MySQL, AspiTurf,
VPN, contournement ou scraper de cotes.

## État réel au 12/10/2026

- Audit exécuté dans le runtime cloud : **46 courses, 619 participants,
  huit dates 2024/2025 et le 05/10/2026, 12 hippodromes**.
- Les 149 courses du programme 05–11/10 comprennent **99 françaises et
  50 étrangères**. Les trois collecteurs existants sont corrigés pour FRA.
- Cinq historiques individuels : 10 performances pour trois chevaux,
  3 pour Fabius Ors et 2 pour Over The Hill, avant le 05/10/2026.
- Avant-course vérifié sur deux captures prospectives du 13/10 : 28 partants,
  sans résultats. Les historiques actuels sont filtrés par date.
- **27 tests réussis**. Pilote régression conditionnelle entraîné sur 14 courses
  de 2024, sélection sur 12 courses de 2025, test sur 14 courses du 05/10/2026.
- Test exploratoire : log loss 2,4845 (uniforme 2,6444), Brier 0,8960
  (uniforme 0,9282), premier choix gagnant 1/14. **NO BET : modèle non validé.**
- Six courses candidates mises en quarantaine : cinq réponses historiques vides,
  une ambiguïté d'identité. Aucune exclusion silencieuse ni donnée inventée.
- Audit et récupération des archives exécutés avec succès sur GitHub Actions.
  État des workflows pilote/prédiction : voir `WORK_PROGRESS.md`.
- Comparateur de cotes manuelles testé sur fixtures ; aucune capture réelle reçue.

## Documents et preuves

- [Backtest expérimental](reports/BACKTEST_PILOT_V1.md).
- [Audit de faisabilité](reports/AUDIT_FEASIBILITY.md).
- [Cinq historiques détaillés](reports/FIVE_HORSE_HISTORIES.md).
- [Architecture proposée](docs/ARCHITECTURE_PROPOSAL.md).
- [État et prochaine action](WORK_PROGRESS.md).
- [Règles des captures de cotes](docs/MANUAL_QUOTES.md).
- `evidence/` : captures JSON.gz, URL, UTC et empreintes SHA-256.
- `reports/` : JSON reproductibles, contrôles qualité et résultats des tests.

Les archives sont des données source : des champs de marché peuvent y figurer
incidemment, mais ils ne sont jamais des entrées du modèle ou des variables de
sélection. Les captures manuelles restent l'unique entrée pour l'EV avant départ.

## Rejouer dans un environnement cloud

Python 3.12, bibliothèque standard seulement. Rien à installer sur le PC de
l'utilisateur. Sur GitHub, le workflow `Turf Lab bounded phase A audit` rejoue
l'audit borné, utilise les captures déjà présentes et sauvegarde les résultats
par commit ; les artefacts temporaires sont seulement une copie de diagnostic.

```bash
python -m unittest discover -s tests -v
python -m scripts.audit_phase_a
python -m scripts.audit_horses
python -m scripts.audit_temporal
python -m scripts.audit_before_race
python -m scripts.audit_opposition
python -m scripts.build_audit_report
```

Les dates de ce premier audit sont intentionnellement figées. Une nouvelle
capture doit avoir un nouveau répertoire d'évidence. Ne pas effacer les captures
anciennes pour les remplacer par des informations connues plus tard.

Les archives Actions d'origine ont été récupérées, contrôlées et conservées dans
`data/reference/`. Les nouveaux bruts et partitions sont sauvegardés dans Git,
les artefacts temporaires ne constituent pas le stockage principal.

```bash
python -m scripts.reconcile_reference
python -m scripts.build_pilot
python -m scripts.backtest_pilot
python -m scripts.predict_race --date AAAA-MM-JJ --reunion R --course C
```

Le workflow de prédiction accepte une exécution manuelle ou une modification de
`config/prediction_request.json`. Il produit un JSON de probabilités, un rapport
HTML mobile et un modèle de transcription manuelle des cotes. Les captures sont
horodatées et conservées séparément. Un départ passé provoque un arrêt.

Aucune collecte massive. Un suivi prospectif borné est activé : deux courses
maximum par jour, pour les départs du 13 au 26 octobre 2026, modèle figé.
Les résultats sont vérifiés jusqu'au 28 octobre ; les appels PMU cessent ensuite.
Première exécution et sauvegarde réussies : run 38287036836.
Voir WORK_PROGRESS.md pour les résultats et la reprise. Le pilote
ne justifie pas de pari : volume faible, historique rétrospectif et validation
prospective encore nécessaire. Aucun ROI n'est calculé.
