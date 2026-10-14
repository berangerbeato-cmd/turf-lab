# V6 parallèle — protocole du 14 octobre 2026

Observation uniquement, sans mises, sans cotes, sans réentraînement.

- Premier lot : les six courses du 14 octobre déjà déclarées dans config/v5_followup.json. Aucun remplacement selon les résultats.
- Modèles : V5 combined et V6 combined, poids et code de features vérifiés par models/v6_holdout_frozen.json.
- Chaque nouvelle capture V5 produit un fichier séparé predictions_v6, avec les mêmes données, la même empreinte historique et un horodatage V6 réel antérieur au départ. Aucun ajout rétroactif aux anciennes prédictions.
- Reproduction exacte de V5 obligatoire. Les fichiers V5 existants restent inchangés. Tout échec V6 est visible dans v6_rejected du rapport de capture.
- Score apparié V5/V6 calculé exclusivement sur les captures V6 valides, sélectionnées par horodatage avant lecture des résultats. Ne pas comparer des agrégats fondés sur des lots différents.
- Contrôle du modèle figé, de l'empreinte du fichier V5 source, des partants, identités, drivers, entraîneurs, ferrures, âge et sexe. Arrivée définitive concordante obligatoire. Aucun recalcul des probabilités après résultat.
- Collecte et suivi restent bornés au protocole existant, jusqu'au 20 octobre inclus. Le score V6 peut effectuer au maximum 12 requêtes de résultat par exécution, en plus des 12 de V5, uniquement après départ.
- Les exécutions prévues sont à 09 h et 23 h, heure de Paris (déclenchement GitHub susceptible de retard). Le déploiement déclenche aussi une première exécution.
- Six courses servent à vérifier le fonctionnement, pas à établir une performance. L'extension à plusieurs centaines de courses exige un nouveau lot prédéfini ; elle n'est pas activée ici.

V5 reste la référence. Aucune promotion automatique de V6. Les captures de cotes fournies par l'utilisateur feront l'objet d'une étape distincte.
