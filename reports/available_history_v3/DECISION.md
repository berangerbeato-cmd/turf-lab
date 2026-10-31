# Décision — historique disponible V3

Deux candidats sportifs ont été réentraînés sur les **17 532 courses existantes**. Aucune collecte supplémentaire. Les 6 398 courses de 2025 sont séparées en sélection (3 156) puis calibration (3 242). Les 4 661 courses de janvier à septembre 2026 servent à une évaluation chronologique déjà examinée, non à un test vierge.

Le candidat retenu sur 2025 utilise les cinq derniers départs disponibles sans limite de 60 jours et quatre variables résumant les vingt derniers résultats connus pour les disqualifications. Les autres variables restent celles du jeu Classic existant. Les statistiques sont calculées avant tous les résultats de la journée cible. Les paramètres de calibration sont estimés sur le second semestre 2025 seulement.

| Modèle | Gagnants en premier choix | Taux | Log loss ↓ | Brier ↓ |
|---|---:|---:|---:|---:|
| V6 opérationnel | 1 162 / 4 661 | 24,93 % | 2,172167 | 0,854913 |
| Classic opérationnel | 1 229 / 4 661 | 26,37 % | 2,127534 | 0,846505 |
| Nouveau candidat | 1 255 / 4 661 | 26,93 % | 2,115859 | 0,844000 |

Le gain de log loss face à Classic est de −0,011674, avec intervalle exploratoire à 95 % par semaines [−0,016583 ; −0,006389]. Le Brier progresse aussi. Les 26 gagnants supplémentaires donnent +0,56 point de réussite, mais l'intervalle de cet écart [−0,18 ; +1,29 point] inclut zéro : ne pas affirmer une hausse du taux de réussite démontrée.

L'ablation sans variables DQ donne déjà une log loss de 2,116738. L'apport supplémentaire des variables DQ est faible (0,000879) ; il n'est pas démontré séparément par ce résultat.

## Ce qui a été récupéré sans collecte

Sur 368 988 participations actives dans les trois jeux, 66 890 retrouvent au moins une course antérieure alors que la fenêtre de 60 jours les laissait sans historique. Ce ne sont ni 66 890 chevaux distincts, ni des courses nouvellement collectées. 23 646 participations restent sans historique disponible. Les exclusions anciennes du jeu figé sont conservées.

## Biais encore présents

Le contrôle séparé par cotes porte sur **2 578 courses communes** avec tableaux de référence PMU complets, horodatés avant le départ prévu selon les archives. Ces archives rétrospectives ne prouvent pas la disponibilité réelle des prix à une décision passée ; aucun ROI ni prix ZEturf exécutable n'en est déduit.

- Chevaux cotés entre 1 et 3 : nouveau candidat 26,86 % de probabilité moyenne, contre 40,74 % de gagnants observés (Classic : 24,80 %).
- Chevaux cotés 80 ou plus : nouveau candidat 1,71 %, contre 0,09 % observé (2 victoires / 2 227 participations ; estimation fragile).
- Sur cette même cohorte, log loss du candidat 2,108413 contre 1,941194 pour les probabilités de marché normalisées.

**Conclusion : amélioration sportive mesurée mais modeste, biais favoris/outsiders encore importants.** Conserver ce candidat et ses paramètres pour comparaison future ; ne pas remplacer automatiquement V6/Classic et ne pas reprendre les recommandations. Aucun poids opérationnel, aucune prévision archivée ni règle de recommandation n'a été modifié.

Validation : 207 tests, 5 ignorés ; workflow GitHub 41212833098 terminé avec succès. Le calcul local indépendant reproduit les résultats. Modèles, sélection avant test, empreintes des données, scores mensuels et prédictions sauvegardés. Le diagnostic complémentaire se reproduit avec `python -m scripts.audit_available_history_market` après l'expérience.
