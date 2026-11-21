# Turf Lab — deux chaînes Value Correction V2, comparaison appariée (recherche)

## Question posée
La correction d'historique V1.1 améliore-t-elle le calcul de value lorsqu'on lui applique **exactement les mêmes coefficients V2 Cotes** et **exactement les mêmes cotes pré-départ** que la V3 gelée ?

Chaînes comparées :
- **Référence** : Available History V3 gelée → Value Correction V2 gelée.
- **Challenger expérimental** : History Repair V1.1 gelée (correction de cinq caractéristiques, mêmes coefficients sportifs V3) → **la même** Value Correction V2 gelée.

**IMPORTANT** : V2 Cotes a été entraînée sur la V3 historique. Les coefficients V2 ne sont pas adaptés/recalibrés pour V1.1 dans cette expérimentation. Toute probabilité du challenger est un simple transfert exploratoire ; aucune confirmation de calibration ni d'EV réelle.

## Sécurités de mesure
- Vérifie SHA-256 des poids V2 et de la configuration active, empreinte et température V3, version et prévision initiale du challenger.
- Exige un tableau complet de cotes décimales identiques, avec preuves des captures et noms de chevaux correspondants, tous **PARTANT** et aucune cote manquante. Vérifie l'horodatage d'observation avant départ (15 min max) et le calcul initial V2 dans les 5 minutes suivant la cote.
- Recalcule la chaîne V3+V2 et **exige** qu'elle reproduise, à 1e-10 près, chaque probabilité archivée de la V2 originale.
- Distingue `PRESTART_PAIRED_ON_DEMAND` (sidecar V1.1 créé lui-même avant départ ; capture de cotes fraîche) et `RETROSPECTIVE_PAIRED_REPLAY` (recalcul tardif sur données pré-départ).
- Une capture à la demande reste une **sélection non aléatoire de courses**, distincte de la cohorte sportive déterministe (qui n'a pas de cotes ZEturf garanties).
- Aucun entraînement, recommandation, mise, modification de V3, V2 ou des archives historiques.

## Fichiers
- `turf_lab/value_history_pair.py` : calcul apparié, contrôles de provenance, rapport de probabilités et EV indicatives séparées.
- `scripts/run_prediction_request.py` : si une demande de prédiction fournit un tableau complet, écrit facultativement `value_history_pair_v1.json` à côté de la prévision et du `comparison.json` original. Une erreur sur le challenger ne bloque pas la V3/V2 ou l'enregistrement habituel.
- `scripts/evaluate_value_history_pair.py` : rejeu rétrospectif Reims à partir des seules preuves de 18h27 et prévisions d'origine, avec **étiquette RETROSPECTIVE**, pas prospective.
- `scripts/score_value_history_pair.py` : scores appariés des **seuls** `value_history_pair_v1.json` véritablement pré-départ contre les arrivées officielles avec identité et statut partant inchangés. Sépare les exclus et en attente. Mesure log loss, Brier, top1 et nombre de courses; **ROI non calculé** en absence de cotes acceptées et rapports opérateur garantis.
- `.github/workflows/value_history_pair.yml` : tests de garde-fous, rejeu de Reims, premier contrôle de bilan prospectif.
- `.github/workflows/recent_history.yml` : reprend les scores après la synchronisation des résultats.

## Premiers constats (Reims R4C5, 21/11/2026)
Cotes ZEturf capturées 18h27 CET, départ 18h37 CET. La correction V2 originale a été calculée à 18h30, AVANT départ. Le calcul V1.1 + V2 est postérieur au résultat et **n'est donc pas** une prédiction prospective.

- Gagnante n° 2 à cote 8,1 : V3+V2 9,7969 % ; History Repair V1.1+V2 9,6692 %.
- N° 6 à cote 6,5 : V3+V2 15,2441 % ; V1.1+V2 15,0455 %.
- Zéro EV positive sur 14 chevaux dans chacune des deux chaînes.
- Comparaison reproductible de la chaîne V3+V2 originale : différence max ~1e-16.

**Une course n'établit ni amélioration statistique, ni rentabilité, ni valeur prédictive validée chez ZEturf**. Ne pas associer le résultat V1.1+V2 à un conseil de jeu sur la course déjà courue.

## Décision
Poursuivre en **PAPER ONLY / NO BET**. Après un volume significatif de courses avec cotes comparables et arrivée vérifiée, comparer les probabilités conditionnellement aux tranches de cotes, en particulier 20–50, 50–80 et >=80, avec intervalles par journée. Un réentraînement futur de V2 sur les données V1.1 demanderait un **autre modèle et une période d'entraînement distincte**, jamais une réutilisation cachée des résultats de test.
