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
- **17 tests hors ligne réussis**. Aucun modèle entraîné, aucun backtest ni ROI.
- Comparateur de cotes manuelles écrit et testé sur fixtures. La chaîne complète
  capture → prédiction → EV n'est pas encore opérationnelle.
- État du déploiement suivi dans WORK_PROGRESS.md : aucune exécution des nouveaux
  workflows n'est revendiquée. Voir `WORK_PROGRESS.md` avant toute reprise.

## Documents et preuves

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

Le workflow `Recover reference evidence` doit préserver les deux ZIP Actions
originaux avec les empreintes reçues de GitHub. Il n'a pas encore été exécuté
pendant cette session. L'audit public actuel est une observation distincte.

Les phases suivantes restent conditionnées par une sauvegarde durable GitHub
opérationnelle, puis par un pilote historique plus large avec découpage temporel
entraînement/validation/test. La bonne disponibilité des champs n'est pas une
preuve que le modèle sera performant.
