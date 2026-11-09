# Cohorte sportive enrichie — contrôle de faisabilité

Collecte exécutée le 30 octobre 2026. Dates fixées avant récupération : 20, 22, 26 et 28 octobre. Toutes les courses françaises attelées des programmes archivés sont conservées dans le registre, sans remplacement selon les résultats.

## Résultats

- 34 courses prévues, 34 champs complets récupérés, 467 partants et fiches individuelles.
- 55 partants ont une fenêtre de 60 jours non confirmée : moins de cinq départs récents retournés et aucune performance antérieure permettant de borner cette fenêtre. Cela ne prouve pas une donnée manquante : un véritable débutant peut être dans ce cas.
- 26 chevaux ont au moins un résultat récent non exploitable : au total 24 mentions PLACE sans rang, deux ARRETE et un TOMBE. Ces événements ne sont pas convertis artificiellement en places ou supprimés sans signalement.
- 22 courses ont toutes leurs fenêtres étayées ; 12 satisfont aussi le contrôle des résultats récents exploitables. Ce critère ne prouve pas une carrière exhaustive.

| Âge | Partants | Fenêtre non confirmée |
|---|---:|---:|
| 2 ans | 28 | 23 |
| 3 ans | 133 | 25 |
| 4 ans | 134 | 6 |
| 5 ans | 59 | 0 |
| 6 ans | 76 | 0 |
| 7 ans | 25 | 1 |
| 8 ans | 6 | 0 |
| 9 ans | 5 | 0 |
| 10 ans | 1 | 0 |

## Décision

Pas de nouveau modèle entraîné ni promu. Cette collecte est un test de couverture de quatre journées proches, pas un jeu représentatif avec validation indépendante. Écarter les fenêtres non confirmées pénaliserait particulièrement les jeunes chevaux : 23 des 28 deux ans sont concernés. Cela pourrait produire une validation trompeuse sur les seuls chevaux expérimentés.

La prochaine collecte doit retrouver les résultats officiels des courses correspondant aux rangs absents, distinguer les débuts de carrière des omissions et élargir les dates sur plusieurs saisons. Il faut ensuite fixer les périodes entraînement/validation/test avant toute sélection de modèle. Les périodes déjà inspectées ne deviennent pas un test vierge.

Les cinq variables exportées utilisent uniquement des performances datées strictement antérieures au jour cible. Les cotes, compteurs de carrière de la fiche courante et résultat cible ne sont jamais utilisés comme variables. Les labels gagnant/disqualifié sont attachés séparément après le calcul. Âge conservé uniquement pour le diagnostic de couverture. Les modèles V6 et Classic restent figés ; leurs autres variables (Elo, entourage, tandem) ne sont pas reconstruites ici.

Les réponses ont été récupérées après les courses : les dates antérieures évitent la fuite directe des résultats cibles, mais ne transforment pas ces données en captures originales avant départ. La source peut omettre des performances.

## Reproduction et preuves

`python -m scripts.collect_sport_cohort --max-requests 0` restaure le paquet de preuves si nécessaire et rejoue sans réseau. Une valeur positive autorise une collecte bornée des fiches absentes, avec huit requêtes simultanées au maximum. Le protocole enregistré interdit une modification silencieuse des dates. Les erreurs et courses exclues restent dans coverage.json.

evidence.tar.gz contient les réponses brutes compressées et leur manifeste (URL, heure de récupération, empreinte SHA-256). coverage.json verrouille les empreintes des archives quotidiennes, du manifeste et du jeu exporté. dataset.json contient uniquement les variables sportives, les étiquettes et les diagnostics. Les archives de modèles ne sont pas modifiées.

Validation : suite de 203 tests, sans échec, dont 5 ignorés ; replay des 467 fiches effectué sans requête supplémentaire. Aucune collecte récurrente ni reprise des recommandations de paris n’est activée.
