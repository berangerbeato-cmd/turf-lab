# TURF LAB — audit de faisabilité du 12 octobre 2026

## Conclusion vérifiée

**Les données permettent de préparer un pilote, sous conditions.** L’audit porte sur 46 courses françaises de trot attelé et 619 participants déclarés, dans 12 hippodromes. Aucun modèle n’est entraîné et aucune performance prédictive ou rentabilité n’est annoncée.

**Correction importante : les 149 courses des programmes du 5 au 11 octobre comprennent seulement 99 courses françaises et 50 courses étrangères.** Les scripts d’origine ne filtraient pas le pays.

Les 14 courses et 203 participants du 5 octobre sont retrouvés dans une nouvelle lecture PMU. Le run GitHub de référence est bien réussi, mais ses ZIP originaux n’ont pas pu être téléchargés par le connecteur. Cette nouvelle lecture ne prétend donc pas vérifier leur contenu octet par octet.

L’état de publication et les exécutions cloud sont consignés dans WORK_PROGRESS.md et GitHub Actions. Les chiffres ci-dessous proviennent des preuves archivées ; ils ne constituent pas une validation du modèle.

## Méthode et couverture

Huit dates 2024/2025, quatre courses au plus par date, sélectionnées pour varier hippodromes et départs ; toutes les courses françaises d’attelé du 05/10/2026. Cet échantillon de disponibilité ne représente pas la distribution complète des courses et ne sert pas à mesurer un modèle.

| Date | Courses françaises au programme | Courses auditées | Participants audités |
|---|---:|---:|---:|
| 2024-01-28 | 20 | 4 | 49 |
| 2024-05-15 | 7 | 4 | 58 |
| 2024-07-13 | 29 | 4 | 55 |
| 2024-11-01 | 58 | 4 | 56 |
| 2025-01-26 | 31 | 4 | 52 |
| 2025-05-14 | 7 | 4 | 57 |
| 2025-08-09 | 40 | 4 | 42 |
| 2025-11-01 | 55 | 4 | 47 |
| 2026-10-05 | 14 | 14 | 203 |

Hippodromes réellement audités : ARGENTAN, BEAUMONT DE LOMAGNE, CAEN, CAGNES/MER, ENGHIEN, LAVAL, LE CROISE LAROCHE, LES SABLES D OLONNE, LYON LA SOIE, NANTES, NIMES, VINCENNES.

Collecte principale : 107 réponses, statuts {'200': 107}. Évidence complémentaire incluse : 1228 réponses conservées au total. Rejouer les analyses utilise le cache et vérifie les empreintes SHA-256.

## A1 — cinq chevaux, historique arrêté avant le 05/10/2026

Sélection selon les caractéristiques avant course, sans utiliser le résultat du 5 octobre. Les détails course par course figurent dans `FIVE_HORSE_HISTORIES.md` et dans le JSON correspondant.

| Cheval | Profil | Courses antérieures disponibles | Dernières retenues |
|---|---|---:|---:|
| FABIUS ORS | Importé, historique français court | 3 | 3 |
| LORD ON WAY | 5 ans, plusieurs victoires dans la musique | 33 | 10 |
| OVER THE HILL | 2 ans, jeune cheval en autostart | 2 | 2 |
| GISARO | Cheval âgé, recul | 124 | 10 |
| MAZURKA DE BELI | Jument de province, disqualifications fréquentes | 13 | 10 |

Sur les 35 performances retenues : dates, hippodromes, distances, drivers, entraîneurs et nombre de participants sont disponibles pour toutes. Les chronos peuvent manquer normalement en cas de disqualification, mais aussi sur certaines courses de province. Les courses montées éventuelles sont conservées et identifiées ; ne pas les assimiler à l’attelé.

L’historique de l’importé est incomplet par rapport à sa musique. Le jeune cheval peut réellement avoir peu couru : aucun historique fictif n’est ajouté. Le meilleur chrono dans ces dix courses n’est **pas** un record personnel de carrière.

Ferrures : codes `0–8` décodés à partir du client officiel PMU, valeur brute conservée. Une ferrure absente reste inconnue. Les changements sont calculables entre deux observations datées, sous réserve de couverture.

Opposition détaillée : {"horse_id": "LORD ON WAY-ONLY WAY-FABULOUS WOOD", "parameters": {"date": "2026-09-21", "racecourseCode": "CAP", "raceNumber": 7, "language": "fr"}, "available": true, "runs": [{"race_date": "2026-09-21", "field_size": 15, "opponents_returned": 15, "participant_fields": ["comparableOpponents", "distanceCovered", "horseName", "lastOdds", "mileageReduction", "place", "railPosition", "riderName", "runnerNumber", "shoes", "timeRecord", "trainerName", "trainerOpinion"]}]}.

## A2 — profondeur et temporalité

Les quatre appels d’historique détaillé associés à une course ancienne donnent 297 lignes, avec **0 ligne à la date cible ou après** dans cet échantillon. Ils exposent jusqu’à cinq performances par cheval. Ce contrôle ne prouve pas une garantie générale de l’API ni la date de publication originelle.

| Course cible | Chevaux | Performances | Date la plus ancienne | Date la plus récente |
|---|---:|---:|---|---|
| 2024-01-28_R1C1 | 12 | 60 | 2023-05-08 | 2024-01-22 |
| 2024-05-15_R1C1 | 16 | 78 | 2021-06-04 | 2024-05-11 |
| 2025-01-26_R1C1 | 16 | 80 | 2024-03-02 | 2025-01-20 |
| 2025-05-14_R1C1 | 16 | 79 | 2024-07-20 | 2025-05-11 |

L’endpoint individuel `light-performances` renvoie l’historique connu aujourd’hui, y compris la course cible et les courses ultérieures éventuelles. Il exige un filtrage strict par date ; les résumés de carrière contemporains ne doivent pas alimenter un ancien backtest.

Contrôle prospectif : 2 courses du 13/10/2026 (LYON-PARILLY, VINCENNES), 28 partants, capturées avant leur départ programmé, sans arrivée, chrono ou commentaire après-course. Voir `prospective_audit.json` pour les heures UTC exactes.

## A3 — disponibilité des champs participants

Taux = valeurs non nulles et non vides / participants déclarés, non-partants inclus. Un zéro peut être une valeur valide. Présence ne signifie ni utilité prédictive ni preuve de disponibilité historique avant course.

| Variable | 2024 (n=218) | 2025 (n=198) | 2026 (n=203) | Interprétation |
|---|---:|---:|---:|---|
| Identité PMU directe | 0/218 (0.0%) | 89/198 (44.9%) | 203/203 (100.0%) | Identifiant ; absent de certaines archives |
| Nom | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Avec père et mère pour identité composite |
| Père | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Identité |
| Mère | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Identité |
| Âge | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Avant course |
| Sexe | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Avant course |
| Musique | 216/218 (99.1%) | 190/198 (96.0%) | 203/203 (100.0%) | Avant course ; dates non incluses |
| Driver | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Déclaration avant course, changements possibles |
| Entraîneur | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Déclaration avant course |
| Ferrure déclarée | 151/218 (69.3%) | 115/198 (58.1%) | 121/203 (59.6%) | Absent ≠ ferré |
| Distance individuelle | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Avant course ; recul à calculer |
| Gains de carrière | 197/218 (90.4%) | 190/198 (96.0%) | 203/203 (100.0%) | Centimes ; caractère figé historique à contrôler |
| Nombre de courses | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Couverture/périmètre du compteur non garanti |
| Victoires cumulées | 218/218 (100.0%) | 198/198 (100.0%) | 203/203 (100.0%) | Recalculer avant chaque course |
| Avis entraîneur | 197/218 (90.4%) | 190/198 (96.0%) | 203/203 (100.0%) | Neutralité et date de publication à contrôler |
| Place au départ | 83/218 (38.1%) | 79/198 (39.9%) | 38/203 (18.7%) | Surtout autostart ; absence pas une position nulle |
| Rang final | 171/218 (78.4%) | 152/198 (76.8%) | 149/203 (73.4%) | Après course : cible seulement |
| Incident | 42/218 (19.3%) | 45/198 (22.7%) | 54/203 (26.6%) | Après course ; absence souvent normale |
| Temps obtenu | 171/218 (78.4%) | 152/198 (76.8%) | 144/203 (70.9%) | Après course ; millisecondes |
| Réduction kilométrique | 171/218 (78.4%) | 152/198 (76.8%) | 144/203 (70.9%) | Après course ; millisecondes par km, pas record personnel |
| Commentaire après course | 0/218 (0.0%) | 0/198 (0.0%) | 83/203 (40.9%) | Exclu des features de la course cible |

## Variables directes, dérivées et non validées

| Famille | Accessible | Traitement ou limite |
|---|---|---|
| Forme, régularité, disqualifications | Musique et performances datées | Recalcul avant chaque course ; séparer attelé/monté et absences |
| Repos, fréquence des courses | Dates des performances | Calculer les écarts ; couverture limitée = fréquence sous-estimée possible |
| Distance, piste, corde | Distance, hippodrome, corde et texte des conditions | Grande/petite piste et surface pas uniformément structurées ; pas de table externe inventée |
| Départ | 15 autostarts explicites sur 46 | Les 31 autres restent « non précisé », pas automatiquement « volté » |
| Recul | Distance individuelle et distance de base | Différence en mètres ; valider les unités et le parcours |
| Ferrure et changement | Déclaration et historique, avec manquants | Pas d’imputation « ferré » ; changement calculé seulement entre observations connues |
| Driver, entraîneur, tandem | Noms à chaque performance | Taux historiques à calculer sur une fenêtre antérieure, avec lissage et effectif |
| Gains, âge, sexe, catégorie | Champs participants et conditions | Gains en centimes, conversion /100 vérifiée dans le client officiel ; plafonds dans texte à parser avec validation |
| Opposition | Allocation, taille du peloton et détail de performance testé | Ne pas traiter la liste top-5 de l’ancien endpoint comme tout le peloton ; Elo nécessite des lignes complètes |
| Parcours similaires | Date, distance, hippodrome et type de départ quand connu | Agrégations antérieures seulement ; échantillon insuffisant pour quantifier leur intérêt |
| Météo | Prévision au niveau de la réunion quand fournie | Archive récupérée après coup ≠ prévision connue avant course ; garder datePrevision |
| Terrain | Certaines structures trackCondition | measureTimestamp=0 seul est un placeholder, pas un état du terrain connu |
| Avis entraîneur | Champ structuré ; parfois NEUTRE | Vérifier date et fréquence des avis ; pas d’assimilation à une information forte |
| Records personnels | Pas de record de carrière vérifié dans ce test | Le champ tempsObtenu est le résultat de la course, timeRecord du détail est aussi une durée de course |

## Contrôles de qualité et fuites

Statut des cibles victoire : **PASS_WIN_LABELS_WITH_WARNINGS**. 46 courses avec un seul gagnant ; aucun désaccord entre gagnant participants et arrivée de course. Aucun doublon numéro/identité dans les pelotons testés.

15 non-partants ; 124 disqualifiés/distancés, dont 4 incidents DISTANCE ; 2 arrêtés. 6 partants sans rang ni incident explicatif : ne pas leur inventer un rang pour un modèle de classement.

Identité composite reconstruite exactement pour 327 lignes sans idCheval, à partir du nom et des deux parents. Cela ne constitue pas un identifiant universel garanti ; conserver les composants et rechercher les collisions lors de l’extension.

Contrôle des unités : 467 couples temps/réduction/distance comparables ; écart absolu médian 0.0625 s, maximum 0.1400 s après conversion des millisecondes. Cet accord est compatible avec les arrondis observés.

Liste d’exclusion du modèle : cotes et rapports, pronostics de marché, ordre d’arrivée de la course cible, chrono de la course cible, commentaires après-course, météo finale non horodatée, statistiques/record de carrière recalculés aujourd’hui. La simple suppression du champ résultat ne suffit pas : chaque agrégat doit utiliser uniquement des courses antérieures.

## A4 — décision et étapes restantes

**GO conditionnel pour un pilote limité ; HOLD pour collecte massive et prédiction utilisable.** Pas de base définitive créée. La proposition de stockage et de backtest est dans `docs/ARCHITECTURE_PROPOSAL.md`.

Conditions avant extension : sauvegarde GitHub opérationnelle ; contrats d’identité et de temporalité testés ; règles explicites pour les manquants ; échantillon de training plus large, chronologique, figé. Les 46 courses de cet audit ne justifient aucune promesse de qualité prédictive.

Sources complémentaires : PMU apporte déjà l’historique requis pour le pilote. LeTROT a été identifié comme complément officiel éventuel pour les records et conditions, mais aucune collecte LeTROT n’est intégrée ni annoncée opérationnelle. Aucun abonnement, scraper de cotes ou API payante.

Les cotes resteront un import manuel horodaté. Le comparateur EV a des tests hors ligne : absence de modèle validé, convention de cote inconnue, course incohérente, cotes périmées ou partants incompatibles imposent NO BET. Il ne constitue pas encore une chaîne de prédiction de course.

## Reproduction

```bash
python -m scripts.audit_phase_a
python -m scripts.audit_horses
python -m scripts.audit_temporal
python -m scripts.audit_before_race
python -m scripts.audit_opposition
python -m scripts.build_audit_report
python -m unittest discover -s tests -v
```

Les dates de l’audit sont figées. Le replay utilise les captures existantes. Une capture nouvelle doit avoir son propre répertoire/version ; ne pas écraser un ancien instantané.

Sources vérifiables :
- [Dépôt initial](https://github.com/berangerbeato-cmd/turf-lab).
- [Exécution de référence](https://github.com/berangerbeato-cmd/turf-lab/actions/runs/38238010891).
- API PMU publique, URL et SHA-256 de chaque réponse dans les manifestes `evidence/*/manifest.json`.
- Contrat d’historique et unités : JavaScript public officiel PMU, URL et empreinte dans `evidence/official_client_history_contract.json`.
