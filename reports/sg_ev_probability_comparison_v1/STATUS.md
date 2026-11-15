# Comparatif SG — implémentation du 15 novembre 2026

Les cinq règles sont implémentées dans `turf_lab/sg_strategy_comparison.py` : top3, top4, P>=10%, P>=15%, P>=20%, toutes avec EV>=10%, 1 EUR fictif par cheval. Rang calculé avant filtrage EV, égalités par numéro. Date de début : 16 novembre ; Beaumont est exclu du suivi prospectif.

## Circuit opérationnel

`scripts.run_prediction_request` archive la première sélection admissible avant départ dans `selections/`. Les prochaines demandes avec cotes complètes alimentent le comparatif ; aucune collecte autonome de cotes ZEturf. Une demande inéligible reste explicitement signalée dans request_status. Le workflow de prédiction sauvegarde les sélections sans modifier les modèles.

`scripts.score_sg_strategies` rapproche les sélections des fichiers `settlements/<race_id>.json`. L'absence de rapport payé laisse la course PENDING. Le workflow `sg_strategy_comparison.yml` exécute les tests et le scoreur lors de l'ajout de règlements. Pas de pari automatique.

Un règlement doit contenir : race_id, operator (identique aux cotes), verified=true, final=true, source_evidence, observed_at (avec fuseau, après départ), winner_numbers, sg_total_return_per_eur (clés numéros sous forme de chaînes, rapport réel incluant mise ; perdant 0, remboursement 1). Tous les chevaux sélectionnés par au moins une règle doivent avoir un rapport. Un changement de partants doit être signalé avec field_changed=true et provoque REVIEW.

Le résumé distingue toutes les courses et celles sans alerte d'historique : mises, retours, bénéfice net, ROI, fréquence gagnante, perte maximale cumulée par course. Les résultats futurs ne seront pas assimilés aux cotes capturées.

## Validation et limites

33 tests ciblés réussis localement : frontières de seuils, chronologie, cotes incomplètes, modèle modifié, opérateur, rapports manquants, ex aequo, drawdown, faux doublons d'hippodromes et contrôles existants. Aucun historique prospectif encore disponible pour ces nouvelles règles : zéro course n'est une preuve de rentabilité.

Le diagnostic des historiques et la sensibilité corrigée sont dans `reports/history_reconciliation_2026-11-15/`. L'enrichissement est expérimental ; les poids V3 et les anciennes prévisions restent inchangés. Validation plus large nécessaire avant promotion. Premier bilan après 200 courses réglées purement descriptif, puis confirmation sur période distincte.
