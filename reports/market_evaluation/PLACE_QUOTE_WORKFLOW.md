# Comparer une sélection placée avec un rapport probable

Statut : recherche uniquement. Aucun pari envoyé, aucune rentabilité démontrée.

## Ce qui est disponible

`python -m scripts.compare_place_quote ticket.json quote.json`

Le comparateur travaille sur une sélection déjà calculée et figée. Il ne produit
pas lui-même de prévision et ne récupère pas de rapports ZEturf. La collecte PMU
existante vise le simple gagnant ; elle ne remplace pas une collecte placé ZEturf.

Il vérifie la concordance course / numéro / marché, la chronologie, la présence
des références de preuve, le périmètre étudié et la base monétaire. Les références
de preuve doivent être contrôlées séparément : leur présence ne prouve pas leur authenticité.

## Procédure prospective

1. Calculer avant la course le ticket classique de probabilité maximale, puis sa
   probabilité placée calibrée. Conserver les entrées, la version du modèle et la
   calibration. Le taux global de réussite de 49 % ne remplace pas cette probabilité.
2. Vérifier les partants actuels et l'identité de la course. En cas de changement
   de partants, refaire la prévision ; ne pas réutiliser une ancienne probabilité.
   Le périmètre actuellement étudié reste limité à 10–20 partants sans non-partant.
3. Relever le simple placé du même opérateur, sa fourchette et son unité, idéalement
   10–15 minutes avant départ. Conserver capture ou réponse source et heure du relevé.
   Vérifier séparément l'heure de départ ; ne pas inventer une heure absente.
4. Comparer le rapport probable au seuil 1/p. Conserver les deux bornes : ne pas
   transformer la moyenne de la fourchette en prix certain. Le rapport définitif
   peut sortir de la fourchette affichée.
5. Archiver chaque sélection et chaque relevé, y compris défavorables, avant de
   connaître l'arrivée. Enregistrer ensuite résultat et rapport payé séparément.
6. Évaluer prospectivement la calibration et les résultats des sélections filtrées
   par prix. La calibration actuelle concerne tous les meilleurs tickets du modèle,
   pas un sous-ensemble choisi pour son prix. Aucune règle de mise n'est validée.

## Contrat des fichiers

Ticket : `race_id`, `selection` (liste contenant le numéro), `market="place3"`,
`selection_method="classic_max_probability"`, `field_size`, `nonrunners=0`,
`probability` calibrée, `created_at` avec fuseau, et références `prediction_evidence`,
`calibration_evidence`, `field_evidence`.

Relevé : mêmes `race_id`, `selection`, `market`, puis `operator`, `source_evidence`,
`start_evidence`, `kind="probable"`, `includes_stake=true`, `observed_at`,
`verified_start_at` (avec fuseau), `unit_stake`, `return_low`, `return_high`.
Les montants représentent le retour total, mise incluse, pour l'unité indiquée.

Sortie : seuil d'équilibre, fourchette normalisée par euro et scénarios p×rapport−1.
Ces scénarios ne sont ni un ROI observé, ni une EV validée en pari mutuel.

## Validation

Trois tests couvrent la normalisation de mise et une fourchette qui traverse le
seuil d'équilibre, le rejet des marchés/horaires/valeurs incompatibles et le rejet
des changements de partants ou méthodes de sélection hors périmètre.

Blocage restant : aucune paire réelle prévision placée figée / relevé ZEturf
avant départ n'a été intégrée à cette étape. Aucun scan automatique placé activé.
