# Bilan cumulé Turf Lab au 28 octobre 2026

## Périmètre et sources

Bilan de tous les paris réels documentés retrouvés, du 26 au 28 octobre 2026 inclus. Les recherches dans les échanges antérieurs et les journaux du dépôt n’établissent pas d’autres tickets réglés à inclure. Les anciens pronostics et simulations ne sont pas assimilés à des mises. Le solde du compte ne sert pas à déduire des dépôts, retraits ou paris manquants.

Sources financières : [26 octobre](2026-10-26_actual_bets.md) ; [28 octobre](2026-10-28_actual_bets_results.md). Le 26 octobre, l’utilisateur a confirmé n’avoir conservé que Kapriccio et annulé les autres paris. Ils sont exclus du décompte.

## Tickets réels

Tous les tickets sont des simples gagnants.

| Date | Course | Cheval | Mise | Retour total | Net | Résultat |
|---|---|---|---:|---:|---:|---|
| 26/10/2026 | R3C3 | 7 — Kapriccio | 2.00 € | 13.00 € | 11.00 € | 1er |
| 28/10/2026 | R3C3 | 12 — Kiss Me Julry | 2.00 € | 0.00 € | -2.00 € | 2e |
| 28/10/2026 | R3C3 | 5 — Kate Meteor | 2.00 € | 0.00 € | -2.00 € | Hors arrivée affichée ; statut exact inconnu |
| 28/10/2026 | R3C7 | 3 — Normand Villetot | 2.00 € | 0.00 € | -2.00 € | 2e |
| 28/10/2026 | R3C7 | 2 — Nirvana d’Hermès | 2.00 € | 0.00 € | -2.00 € | Hors arrivée affichée ; statut exact inconnu |

**5 tickets, 10.00 € misés, 13.00 € de retours totaux, 3.00 € de bénéfice net.** Un ticket gagnant sur cinq (20 %), quatre perdants. ROI personnel observé = (13−10)/10 = +30 %. Retour/mises = 130 %. Mise constante : 2 €.

| Journée | Mises | Retours | Net du jour | Net cumulé |
|---|---:|---:|---:|---:|
| 26 octobre | 2 € | 13 € | +11 € | +11 € |
| 28 octobre | 8 € | 0 € | −8 € | +3 € |

Le bénéfice de Kapriccio finance comptablement les quatre pertes suivantes : 11−8 = 3 €. Il ne prouve pas une espérance de gain positive à venir. La série perdante actuelle est de quatre tickets, sur deux courses. Deux chevaux de cette série terminent deuxièmes ; cela ne génère aucun retour en simple gagnant. Aucun gain fictif placé/couplé n’est ajouté.

Le retour de 13 € sur Kapriccio est confirmé dans le journal du ticket réglé (rapport total définitif de 6,50 € par euro). Pour le 28 octobre, les retours nuls sont déduits des tickets SG et des vainqueurs affichés ; les détails de règlement et cotes finales ne sont pas affichés dans les captures.

## Évaluation distincte des modèles

Source : [scores opérationnels](prospective_scores.json), version consultée horodatée 2026-10-28T18:07:08.724017+00:00. Règle : première prédiction valide par course, pas chaque exécution.

Le rapport automatique a huit courses réglées entre le 17 et le 26 octobre et conserve encore les deux courses du 28 octobre en attente. Sur les huit courses : V6 2 premiers choix gagnants sur 8 (25 %) ; Classic 2/8 (25 %). Les courses 2026-10-17_R5C1 et 2026-10-26_R3C2 sont exclues pour changement de partants ; les répétitions d’exclusion de R5C1 ne sont pas de nouvelles courses.

| Course | Premier choix V6 gagnant ? | Premier choix Classic gagnant ? | Source résultat |
| 2026-10-17_R5C6 | Oui | Oui | Rapport automatique |
| 2026-10-17_R5C7 | Non | Non | Rapport automatique |
| 2026-10-18_R4C3 | Non | Non | Rapport automatique |
| 2026-10-25_R5C2 | Non | Non | Rapport automatique |
| 2026-10-25_R5C5 | Non | Non | Rapport automatique |
| 2026-10-26_R3C1 | Oui | Oui | Rapport automatique |
| 2026-10-26_R3C3 | Non | Non | Rapport automatique |
| 2026-10-26_R3C5 | Non | Non | Rapport automatique |
| 2026-10-28_R3C3 | Oui (13) | Non (12, 2e) | Capture utilisateur, provisoire pour l’évaluation |
| 2026-10-28_R3C7 | Non (2) | Non (1) | Capture utilisateur, provisoire pour l’évaluation |

En ajoutant manuellement les deux vainqueurs visibles du 28 octobre, le compteur descriptif devient **V6 3/10 (30 %) et Classic 2/10 (20 %)**. Ce complément n’est pas injecté dans le score officiel : la vérification API et l’intégrité des partants restent nécessaires. Aucun ROI de modèle calculé, faute de règlements opérateur joints pour un protocole de paris défini.

L’ancienne cohorte V6 du 14 octobre existe aussi : [rapport ancien](../v6_prospective_scores.json), cinq courses évaluées, zéro premier choix gagnant ; une sixième en quarantaine pour changement d’identité/driver/entraîneur/ferrure. Elle est présentée séparément, car le pipeline et le périmètre diffèrent du suivi opérationnel V6/Classic. Ne pas la masquer ni fusionner ses métriques sans rapprochement complet des versions et protocoles. Les backtests historiques et autres modèles archivés ne sont pas des paris réels.

## Lecture du bilan et limites

- Le bilan financier documenté est positif de 3 €, malgré la journée du 28 à −8 €. Cinq tickets sur trois courses ne permettent pas de conclure à une méthode rentable.
- Le taux de premiers choix gagnants du modèle et la rentabilité des tickets sélectionnés sont deux mesures différentes. Kapriccio était une sélection de value et non le premier choix brut des modèles.
- Les probabilités d’avant-course restent inchangées. Les cotes d’agrégateurs utilisées pour les recommandations n’étaient pas confirmées en direct : elles ne valident pas les EV annoncées, même si un ticket gagne.
- Plusieurs fenêtres de forme récente sont peu fournies. Cette limite était présente avant les résultats ; les fortes divergences avec les cotes doivent rester des signaux à vérifier et non des rendements promis.
- Les deux places de deuxième aujourd’hui ne démontrent pas que passer systématiquement au placé aurait été rentable : rapports placés et validation correspondante absents.
- Tous les paris annulés et simples pronostics restent hors bilan. Aucune autre journée n’est inventée ; aucun solde initial ou dépôt n’est reconstruit.

Modèles opérationnels inchangés : V6 `fb2aea565cfb` ; Classic full `1c5e0e8f4900`. Aucun réentraînement ni modification des archives sources pour ce bilan.
