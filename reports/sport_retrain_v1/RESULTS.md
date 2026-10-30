# Réentraînement sportif exécuté — 30 octobre 2026

**Décision : candidat non promu. Recommandations toujours suspendues.**

Deux régressions conditionnelles ont été entraînées réellement, sans cotes : une référence à 38 variables et un candidat à 40 variables, avec les mêmes paramètres fixés avant calcul. Le candidat reconstruit la forme récente sur les cinq derniers départs observés, distingue les résultats inconnus des défaites et sépare les arrêts/chutes des disqualifications. Les autres 33 variables sportives sont conservées. Ce n'est pas un enrichissement général à partir des 34 courses de diagnostic.

## Données et exécution

- Entraînement : 17 532 courses, mars 2022–décembre 2024.
- Validation : 6 398 courses de 2025 ; température choisie uniquement sur cette période, 1,0 pour les deux modèles.
- Évaluation : 4 661 courses, janvier–septembre 2026, période déjà observée ; comparaison expérimentale, pas test indépendant.
- 376 696 lignes de partants reconstruites ; premières cinq variables modifiées pour 5 097 lignes. 5 099 lignes avec résultat récent inconnu ; 1 258 avec arrêt ou chute récent. Aucun retrait de cheval pour historique court.
- Empreintes des jeux figés, manifestes mensuels et partitions vérifiées ; mises à jour historiques uniquement après toute une journée de courses. Novembre 2024 et l'anomalie Vichy demeurent exclus selon le protocole historique existant.

| Évaluation 2026 | Référence réentraînée | Candidat corrigé |
|---|---:|---:|
| Log loss, plus faible = mieux | 2,127534 | 2,127095 |
| Brier multiclasses, plus faible = mieux | 0,846505 | 0,846366 |
| Premier choix gagnant | 26,37 % | 26,48 % |
| Erreur de calibration globale par tranches | 0,005794 | 0,005939 |

Gain de log loss : −0,000439, intervalle descriptif à 95 % par semaines [−0,001083 ; +0,000315]. L'intervalle contient zéro. Le premier choix gagne cinq courses supplémentaires sur 4 661, sans gain fiable établi ; l'erreur de calibration globale augmente légèrement. Ne pas qualifier ce candidat de meilleur modèle validé.

## Diagnostic face aux cotes, après le calcul

Prix DIRECT PMU rétrospectifs, uniquement descriptifs : ni cotes exécutables avant départ, ni ROI.

| Cote | Probabilité moyenne du candidat | Fréquence gagnante observée |
|---|---:|---:|
| 1 à moins de 3 | 23,44 % | 40,98 % |
| 3 à moins de 5 | 16,00 % | 23,19 % |
| 50 à moins de 80 | 3,76 % | 0,72 % |
| 80 et plus | 2,50 % | 0,51 % |

La sous-estimation des favoris et la surestimation des gros outsiders persistent. Une correction du traitement des rangs manquants ne suffit pas à les expliquer ni à les réparer. Aucune cote n'a servi à entraîner les modèles ou à sélectionner leur température.

## Limites et prochaine étape utile

Les départs absents du périmètre PMU restent inconnus ; l'Elo et les variables d'entourage n'ont pas été reconstruits à partir de carrières exhaustives. Les 34 courses enrichies ne fournissent pas les données historiques représentatives nécessaires à ce travail. Ce candidat traite l'incertitude des résultats présents, pas l'absence de courses entières. Ne pas multiplier les réglages sur 2026 pour obtenir artificiellement un gain.

Pour une véritable validation, préparer un échantillon sportif enrichi couvrant plusieurs périodes, puis un suivi avant-course avec modèle figé et résultats futurs. Le passage en recommandations exige aussi une validation avec cotes horodatées avant départ. Aucun modèle opérationnel, workflow de prédiction ou verrou de suspension n'est modifié ici.

## Reproduction

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m scripts.retrain_sport_v1`

Le script refuse de remplacer un résultat terminé ; pour une reproduction, utiliser une copie de travail et retirer uniquement le dossier généré `reports/sport_retrain_v1` avant exécution, sans changer le protocole ni les sources. Puis `python -m scripts.audit_sport_retrain_prices`.

Les modèles, probabilités course par course, métriques mensuelles/saisonnières/hippodromes, empreintes et paramètres gelés avant évaluation sont joints. Validation logicielle : 215 tests exécutés, aucun échec, 5 ignorés. Ce succès logiciel n'établit pas une rentabilité.
