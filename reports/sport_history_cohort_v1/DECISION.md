# Décision — réentraînement sur historiques enrichis

Exécution achevée le 31 octobre 2026 : https://github.com/berangerbeato-cmd/turf-lab/actions/runs/41188673339 . Collecte, tests, réentraînement et sauvegardes réussis.

384 courses sélectionnées sans leurs résultats, 312 exploitables, 72 exclues pour données indisponibles ou ambiguës. Découpage : 96 courses d’entraînement (2024), 114 de validation (2025), 102 de test (janvier–septembre 2026). Novembre 2024 est absent du jeu source documenté.

Les rapprochements ont ajouté 4 356 observations de départs antérieurs et modifié les cinq variables de forme pour 2 355 participations. Ces nombres sont comptés par cheval et course cible ; ce ne sont pas des courses ou chevaux uniques.

| Variante expérimentale | Gagnants en premier choix | Log loss | Brier | ECE |
|---|---:|---:|---:|---:|
| Réentraînée sur variables archivées | 21/102 (20,59 %) | 2,29839 | 0,88864 | 0,01582 |
| Réentraînée sur forme enrichie | 23/102 (22,55 %) | 2,24577 | 0,87080 | 0,02117 |

Les deux variantes sont réentraînées sur le même petit échantillon ; la première ligne n’est pas une mesure du V6 opérationnel ni du Classic full opérationnel. La régularisation est choisie sur 2025 seulement : 0,1 pour le témoin et 1 pour la variante enrichie. Aucun prix n’entre dans les variables.

L’intervalle exploratoire à 95 % de la différence de log loss est [-0,12728 ; +0,02400], et celui du gain de premier choix est [-4,17 ; +8,00] points. Les deux incluent zéro. Le Brier baisse mais l’ECE augmente : il n’est pas établi que la calibration globale s’améliore.

**Décision : pas de promotion du candidat. V6 et Classic full opérationnels restent figés ; recommandations toujours suspendues.** Le signal est modeste, l’entraînement porte sur seulement 96 courses et les périodes de validation/test ont déjà été examinées dans d’autres expériences. La qualité des données justifie de poursuivre l’enrichissement, pas d’annoncer un avantage de pari.

Suite nécessaire : développer un entraînement enrichi plus large et une collecte prospective horodatée, puis évaluer sans nouveau réglage sur les mêmes 102 courses. Ne pas ajuster les coefficients pour obtenir un meilleur résultat sur ce test.

Reprise reproductible : `python -m scripts.train_sport_history_cohort --max-requests 0`. Les sources sont dans `evidence/sport_history_cohort_v1`, les modèles candidats dans `models/sport_history_cohort_v1`, les vecteurs, empreintes et détails par sous-groupe dans ce dossier. Le workflow sauvegarde les lots dans la branche de recherche et conserve aussi un artefact.

Validation : 203 tests exécutés, aucun échec, 5 ignorés ; workflow achevé avec succès.
