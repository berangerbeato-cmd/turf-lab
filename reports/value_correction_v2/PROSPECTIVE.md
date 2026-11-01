# Validation prospective de la correction SG

La comparaison habituelle des captures calcule désormais un bloc `value_shadow`, distinct du modèle sportif de base. Le circuit existant conserve la capture transcrite, les probabilités sportives, les paramètres et la comparaison dans le dossier horodaté de la course.

Le calcul corrigé exige toutes les cotes du même opérateur et tous les partants, une observation dans les quinze minutes précédant le départ et, en direct, datant de moins de cinq minutes. Les non-partants, tableaux incohérents et empreintes différentes sont refusés. Un calcul réalisé après départ est étiqueté rétrospectif et ne doit jamais entrer dans une validation prospective.

Les seuils de fraîcheur sont des contrôles de données, pas des seuils de rentabilité. Aucun pari ni mise recommandé. La correction a été entraînée sur les références PMU : sa transposition aux cotes ZEturf/Unibet reste à vérifier. Les collectes de cotes seules, sans prévision sportive figée avant départ, ne constituent pas des tests du modèle hybride.

État : intégration prête pour les prochaines demandes de course accompagnées de tableaux complets ; pas d'affirmation de campagne automatique complète ni de nouvelles courses déjà validées. Le rapprochement automatisé avec les rapports payés reste à développer. Ne pas extrapoler aux tiercé/quarté/quinté, qui demandent leur propre modèle d'arrivée et de rapports.
