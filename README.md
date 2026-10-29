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
