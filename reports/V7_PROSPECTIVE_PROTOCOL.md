# V7 expérimentale intégrée au suivi — 14 octobre 2026

V7 ajoute un unique historique de chrono corrigé du contexte à V6. Poids et code figés dans models/speed_v7_frozen.json. Pas de réentraînement ni de promotion automatique. NO BET.

Première intégration : les six courses déjà déclarées du 14 octobre. Une nouvelle capture avant départ est nécessaire même si V5/V6 ont déjà été capturés : aucun calcul V7 antidaté, aucun écrasement des anciens fichiers.

Les fichiers predictions_v7 comparent V6 et V7 sur les mêmes partants et historiques. La reproduction exacte de V6 est obligatoire. Les empreintes des fichiers V5 et V6 sources sont contrôlées lors du scoring. Les changements de partants, identités, entourage, ferrure, âge ou sexe entraînent l'exclusion, sans renormalisation après résultat.

Les nouveaux rapports v7_prospective_scores.json et V7_PROSPECTIVE_SCORES.md restent séparés. Comparaison uniquement entre les deux modèles du même rapport, jamais entre des lots différents. Chaque échec de capture V7 figure dans v7_rejected du rapport de capture.

Suivi borné jusqu'au 20 octobre 2026 ; 09 h et 23 h Paris, avec retards GitHub possibles. Maximum 12 requêtes de résultat supplémentaires par exécution pour V7 après départ (36 au total pour les trois suivis). Aucun élargissement automatique des courses.

La validation mars–mai 2025 est exploratoire. Juillet–août 2025 ne constitue pas un nouveau test pour sélectionner V7. Un autre échantillon indépendant reste nécessaire ; ces six courses valident d'abord le fonctionnement technique. V6 reste la référence opérationnelle.
