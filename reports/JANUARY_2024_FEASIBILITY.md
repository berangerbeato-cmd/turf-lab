# Extension historique : bilan vérifié de janvier 2024

- 31 programmes quotidiens reçus, 1 055 réponses HTTP 200 conservées avec SHA-256.
- 512 courses françaises de trot attelé répertoriées par PMU, 18 hippodromes.
- 142 courses à Vincennes, 370 en province. 6 757 participations, dont 189 non-partants.
- 512 arrivées définitives avec gagnant unique concordant ; aucune quarantaine.
- 133 départs autostart explicitement identifiés ; 379 non précisés, non assimilés à des départs voltés.
- 6 568 participations actives, 4 384 chevaux distincts identifiés ; 2 184 participations (33,25 %) disposent d'une performance antérieure observée dans le mois. Aucune ne dispose encore de cinq performances précédentes dans cette fenêtre.
- Ce mois valide la méthode de collecte et de normalisation, pas la suffisance de l'historique ni la fiabilité prédictive.
- Reproduction depuis le cache : zéro nouvel appel PMU. Sauvegardes intermédiaires par semaine réellement exécutées dans le second run.
- Runs de collecte : 38313938501 et 38315157655, succès. Historiques : 38315576125 et 38315622039, succès, commits de sauvegarde vérifiés.

## Extension retenue avant toute consultation du nouveau test

Neuf mois bornés : janvier à mars 2024, 2025 et 2026. Collecte séquentielle, réemploi de janvier 2024, sauvegardes tous les sept jours. Pas de planification indéfinie, de collecte de cotes ni d'API payante.

Fenêtre des variables : maximum cinq courses strictement antérieures au jour cible et observées dans les 60 jours précédents. Les courses de janvier-février servent uniquement à constituer cet historique. Les fenêtres d'évaluation vont du 2 au 31 mars : entraînement 2024, sélection 2025, test 2026. Elles ne réutilisent pas le test déjà examiné d'octobre 2026.

Seuils de passage fixés dans config/history_extension_protocol.json : calendrier complet, au moins 98 % des courses conservées pour chaque mois, minimum 200 courses par partition, empreintes vérifiées, identités cohérentes. Sinon blocage explicite. Référence uniforme et régressions à deux pénalisations prédéfinies ; sélection sur validation seulement.

Le périmètre reste les courses listées par PMU, et les historiques peuvent manquer de courses hors périmètre. Trois premiers trimestres ne représentent pas trois années continues et ne prouvent pas la généralisation estivale. Le nouveau modèle reste expérimental et ne remplace pas automatiquement le pilote prospectif.
