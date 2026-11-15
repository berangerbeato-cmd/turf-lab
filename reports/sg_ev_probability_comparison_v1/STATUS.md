# Comparatif SG — point de reprise du 15 novembre 2026

Protocole : `config/sg_ev_probability_comparison_v1.json`.

## Réalisé
- Cinq stratégies et mises fictives fixées avant les futures courses ; Beaumont du 15 novembre exclu du test prospectif.
- Vérification du travail existant sur historiques enrichis : 312 courses exploitables, dont 102 de test. Le gain exploratoire ne justifie pas une promotion ; voir `reports/sport_history_cohort_v1/DECISION.md`.
- Diagnostic Beaumont déjà archivé : 11 partants avec historiques incomplets, notamment deux disqualifications du 10. Les prédictions initiales restent inchangées.

## À réaliser — pas encore automatisé
1. Identifier et réconcilier les courses manquantes avec identités et sources vérifiées, puis reconstruire les variables concernées dans une version distincte.
2. Élargir la validation du candidat enrichi et contrôler sa calibration ; ne pas modifier les poids V3 gelés.
3. Implémenter l'archive avant départ des sélections des cinq stratégies et les tests de chronologie, complétude et règlement.
4. Collecter les rapports SG réellement payés du même opérateur ; sans rapport, résultat financier en attente.
5. Produire le tableau comparatif et les pertes maximales. Aucune stratégie déclarée rentable à ce stade.

Les captures utilisateur restent nécessaires pour les cotes ZEturf ; aucune surveillance autonome supplémentaire n'est créée.
