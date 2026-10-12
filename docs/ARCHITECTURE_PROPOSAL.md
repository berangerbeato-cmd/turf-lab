# Architecture proposée — décision conditionnelle à la fin de l'audit

Statut : stockage d’audit opérationnel ; petit pilote normalisé en cours. Pas de base de production.

## Stockage simple et durable

- Code, paramètres, contrats, tests, rapports et `WORK_PROGRESS.md` sur `main`.
- Évidence d'audit limitée en JSON.gz avec manifestes SHA-256, URL, date de
  récupération UTC, identifiant de collecte et version du collecteur.
- Pilote borné : partitions `data/pilot_v1/AAAA/MM/*.jsonl.gz` sur main, empreinte
  des octets décompressés dans le manifeste. 46 courses candidates, sans expansion.
- Extension future : branche `data` dédiée aux petits lots quotidiens JSON.gz
  et JSONL.gz partitionnés par année/mois. Ne pas réécrire les bruts existants.
  Les corrections créent une nouvelle observation, jamais une falsification
  de l'heure de collecte.
- Les artefacts Actions servent au transport et au diagnostic. La copie Git
  vérifiée reste la source durable initiale. Google Drive peut devenir une
  sauvegarde indépendante ; il n'est ni configuré ni nécessaire au prototype.
- À volume important, réévaluer la taille Git avant extension ; aucun backfill
  massif n'est autorisé implicitement par ce document.

## Identités et dates

Course : date civile Europe/Paris + réunion officielle + course officielle.
Conserver également hippodrome et codes source, pour détecter un changement de
numérotation. Cheval : identifiant PMU composite `nom-mère-père`, valeur brute
conservée. Ne jamais fusionner sur le seul nom ; collisions/parents inconnus
doivent être signalés. Driver/entraîneur : libellés source avec table d'alias
versionnée si nécessaire, pas de rapprochement flou automatique.

Conserver séparément : départ programmé, départ réel si connu, date du fait,
date de collecte, heure de publication source et date limite des features.
Un `fetched_at` tardif ne devient jamais une preuve de capture avant-course.

## Séparation des tables logiques

| Table logique | Contenu | Usage |
|---|---|---|
| raw_observations | Réponses exactes, provenance, empreintes | Audit et relecture |
| races | Conditions et métadonnées datées | Contexte |
| runner_snapshots | Déclarations, numéro, distance individuelle, ferrure | Features sous contrôle temporel |
| results | Arrivée définitive, rang, incident, chronos | Cible ; historique seulement si antérieur |
| horse_history | Performances datées, source et couverture | Forme calculée avant chaque course |
| feature_rows | Liste blanche, date limite, version | Modèle sans cotes |
| predictions | Modèle, données, heure et probabilités | Évaluation et restitution |
| manual_quotes | Transcription capture, heure, convention et preuve | EV séparée du modèle |

## Collecte et reprise

Workflow borné, concurrence 1 pour les écritures, validations d'entrée strictes.
Télécharger vers un fichier temporaire, valider JSON, puis écriture atomique.
Reprendre les requêtes absentes ; ne pas masquer les erreurs derrière un statut
« success ». Arrêter sur contrôle d'accès ou restriction ; aucun contournement.
Limiter les nouvelles tentatives réseau et leur délai ; ne pas boucler.
Sauvegarder les lots terminés et le journal même si une autre course échoue.
Un lot contenant des manquants reste « incomplet » et ne passe pas à l'entraînement.

## Garde-fous des variables

Le modèle reçoit seulement une liste blanche de features. Sont exclus : cotes,
rapports, pronostics externes, arrivée/chrono de la course cible, commentaires
après-course, statistiques ou record de carrière actuels non reconstruits.
Les historiques individuels doivent être filtrés strictement avant la date de
la course cible. Le dernier historique retourné aujourd'hui n'est pas un
instantané ancien. Manquant = valeur manquante + indicateur, jamais zéro implicite.

## Modèle et backtest futurs

1. Référence uniforme `1 / nombre de partants effectifs`.
2. Score explicable basé sur résultats passés et risque de disqualification,
   ou régression multinomiale/conditionnelle au niveau de la course.
3. Softmax des scores des partants, somme = 1. Retrait des non-partants puis
   recalcul et nouvelle version de prédiction.
4. Découpage chronologique par courses et dates, sans mélange des partants
   d'une même course. Imputation, standardisation et calibration ajustées sur
   entraînement/validation seulement. Test final figé avant expérimentation.
5. Log loss par course, Brier multiclasses par course (somme des carrés),
   calibration, top-1 avec règle de départage annoncée, effectifs et résultats
   par hippodrome/distance/catégorie/départ. Incertitudes rééchantillonnées par
   jour/réunion, pas par cheval indépendant.
6. Aucun ROI sans historique de cotes observées avant-course ; le rapport
   définitif de paiement ne remplace pas ces observations.

Elo et arbres ne sont que des candidats ultérieurs. Les disqualifiés restent
des perdants pour la victoire, mais sans chrono inventé ni rang artificiel pour
une mise à jour Elo. Les dead-heats exigent une politique de cible explicite et
une règle de paiement distincte ; mettre en quarantaine avant cela.
