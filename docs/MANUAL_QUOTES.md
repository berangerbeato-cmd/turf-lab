# Captures de cotes et EV — contrat prêt, modèle non disponible

L'utilisateur fournit une capture PMU environ 10–15 minutes avant le départ.
La capture ne déclenche jamais un pari. Aucun scraper de cotes n'existe dans
cette chaîne.

## Vérifications obligatoires

1. Date, hippodrome, réunion et course exacts. Si l'un manque, NO BET.
2. Noms et numéros de tous les partants, identités composites PMU, non-partants.
3. Heure de capture avec fuseau, heure de vérification des partants et départ.
   Une heure de réception du message n'est pas automatiquement l'heure des cotes.
4. Cote clairement convertie en **retour décimal total, mise incluse**. Si la
   capture exprime un gain net « x contre 1 », vérifier sa convention puis
   convertir explicitement. Ne jamais additionner 1 par défaut à un nombre PMU.
5. Prédiction produite indépendamment et avant l'observation des cotes, avec
   modèle/version, heure, limite temporelle des features et somme des probabilités.
6. Transcription vérifiée, image conservée avec son empreinte SHA-256. Une
   image illisible ou une correspondance ambiguë impose NO BET.

## Calcul séparé

`EV = probabilité modèle × cote décimale totale − 1`.

Le module `turf_lab.manual_value` ne consulte aucun site et ne modifie aucune
probabilité selon les cotes. Il refuse les données incohérentes, cotes sans
heure, courses commencées, non-partants mal traités et probabilités invalides.

Le seuil EV de 10 % présent dans le code est un **paramètre provisoire de
prudence**, pas un optimum démontré. Il devra être fixé sur validation, sans
optimiser le test final. Toute sortie positive reste une candidature fictive.
Sans modèle validé hors période d'entraînement, le verdict est **NO BET**, même
si le calcul arithmétique est positif. Les rapports finaux PMU peuvent évoluer.

## Format des entrées

Prédiction : `race_id`, `scheduled_start`, `predicted_at`, `feature_cutoff`,
`validation_status`, `uncertainty`, `data_quality_pass`, puis `runners` avec
`horse_id`, `number`, `name`, `status` (PARTANT/NON_PARTANT), `probability`.

Transcription : même `race_id`, `source=PMU_MANUAL_SCREENSHOT`, `observed_at`,
`runners_verified_at`, `image_sha256`, `transcription_verified=true`,
`odds_format=DECIMAL_TOTAL_RETURN`, puis `quotes` avec `horse_id`, `number`,
`name`, `decimal_odds` pour chaque partant actif.

Les fixtures des tests sont purement synthétiques et ne représentent aucune
course réelle ni résultat de modèle.

## Restitution iPhone prévue

Une carte de course : identité et départ, statut/fiabilité, top des probabilités,
puis tableau compact cheval/probabilité/cote/EV. Les points forts et faibles
doivent citer des observations mesurées ; les scénarios restent conditionnels.
Afficher séparément la couverture de l'historique et l'incertitude du modèle.
Cette restitution n'est pas encore produite par un modèle opérationnel.
