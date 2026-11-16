# Décision — validation élargie des historiques V2

Exécution du 16 novembre 2026 achevée avec succès : [workflow](https://github.com/berangerbeato-cmd/turf-lab/actions/runs/43863376874).

**Décision : ne pas promouvoir ce candidat. Le bénéfice de la forme enrichie ne se confirme pas de façon nette sur l’échantillon élargi.** Le modèle de base available_history_v3 reste inchangé. Cette expérience ne valide aucun seuil EV ni stratégie de pari.

## Protocole et couverture

768 courses sélectionnées sans résultats ni cotes, 24 par mois, avec la même graine que la V1. Novembre 2024 reste absent du jeu source documenté. 618 courses sont exploitables et 150 sont exclues : 104 historiques indisponibles, 28 identités historiques ambiguës, 16 conflits de résultat, une identité de course ambiguë et une identité de cheval différente.

193 courses entraînent les coefficients (2024). 115 choisissent la régularisation (janvier–juin 2025). 112 choisissent la température (juillet–décembre 2025). 198 servent au test (janvier–septembre 2026). Les deux variantes choisissent L2 = 0,1 et température = 1,15, avant le calcul du test.

Comparaison de deux modèles expérimentaux réentraînés de 38 variables, dont cinq variables de forme récente enrichies. Ce n’est pas une comparaison directe au V3 opérationnel de 42 variables. Elo, professionnels et tandem restent archivés. Les périodes historiques ont déjà été examinées : il ne s’agit pas d’un nouveau test prospectif vierge.

## Résultats après calibration

| Variante | Premier choix gagnant | Log loss ↓ | Brier ↓ | ECE ↓ |
|---|---:|---:|---:|---:|
| Témoin | 49/198 (24.75%) | 2.23214 | 0.86756 | 0.00515 |
| Forme enrichie | 48/198 (24.24%) | 2.23107 | 0.86700 | 0.00635 |

Écart enrichi moins témoin : log loss −0,00107, intervalle exploratoire à 95 % [−0,02525 ; +0,02292] ; Brier −0,00056 [−0,00715 ; +0,00632] ; premier choix −0,51 point [−3,26 ; +1,92 points]. Tous incluent zéro. Bootstrap apparié par semaine, non corrigé des expériences multiples ; les chevaux peuvent rester dépendants entre semaines.

Sur les 96 courses de test ajoutées par rapport à la sélection V1 : témoin 24 gagnants, enrichi 23 ; log loss 2,21219 contre 2,21444. L’écart de log loss est +0,00225 [−0,02277 ; +0,02736]. Ce sous-échantillon n’établit pas davantage un gain.

## Effet de la calibration

La température sélectionnée sur fin 2025 améliore descriptivement le test des deux variantes : témoin log loss 2,24031 → 2,23214 et ECE 0,01291 → 0,00515 ; enrichi log loss 2,24117 → 2,23107 et ECE 0,01218 → 0,00635. Cela ne constitue pas une validation de cette température pour le V3 actif. L’ECE agrège tous les partants avec des classes de 10 points ; elle ne garantit pas la précision au voisinage des seuils de décision EV.

## Limite des sources pour Elo et les professionnels

Un audit reproductible des 335 réponses historiques V1 disponibles vérifie chaque empreinte source. Sur 20 277 lignes historiques, répétitions comprises, 20 204 listent moins de participants que l’effectif annoncé. Aucun champ entraîneur ne figure dans les 112 143 participants listés. Ces nombres ne sont pas des courses ou personnes uniques. Les listes partielles ne permettent pas de reconstruire honnêtement les confrontations Elo complètes ni les statistiques entraîneur. Voir source_schema_audit.json et scripts/audit_supplemental_history_schema.py.

## Suite utile

Conserver l’enrichissement comme diagnostic de qualité, sans remplacer les probabilités opérationnelles par cette variante. Pour reconstruire Elo et les professionnels, acquérir et rapprocher les champs complets des courses manquantes, avec identités et résultats vérifiés ; les historiques individuels partiels ne suffisent pas.

Comparer top 3, top 4 et seuils de probabilité uniquement dans le suivi SG prospectif déjà prévu, sur probabilités et cotes horodatées avant départ puis rapports officiels. Cette expérience sportive sans cotes ne tranche pas EV ≥ 10 % + top 3 contre top 4. Ne pas régler de nouveaux paramètres pour améliorer rétrospectivement Beaumont ou ce test 2026.

Validation technique : 9 tests V2 réussis sur GitHub ; 4 tests de recherche/calibration et 10 tests historiques exécutés localement (un ignoré). Un test d’intégration synthétique de la chaîne confirme que changer les gagnants du test ne modifie ni les coefficients ni les températures. Les fichiers modèles et les périodes de sélection sont verrouillés avant mesure du test.

Reproduction : `python -m scripts.train_sport_history_cohort_v2 --max-requests 0`. Audit de source : `python -m scripts.audit_supplemental_history_schema`.
