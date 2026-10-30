# Correction sportive sans cotes

Les performances individuelles retrouvées sont maintenant injectées dans une copie des cinq variables de forme récente, et un calcul de sensibilité séparé est exécuté avec les poids figés. Les sorties originales restent inchangées. Aucun prix ne participe au calcul.

Sur R4C8 : Nativa Bella passe de 10,97 % à 19,70 % avec V6 et de 10,16 % à 18,70 % avec Classic. Naranja passe de 12,00 % à 7,83 % avec V6. Ces chiffres ne sont ni une prédiction avant course ni une preuve de calibration : la collecte individuelle a été réalisée après course et le cas a été sélectionné après observation du problème.

Le réentraînement général est bloqué faute d’un ensemble représentatif de vecteurs enrichis sur des périodes distinctes. Les douze historiques individuels de cette course ne suffisent pas. Réentraîner sur les anciennes variables incomplètes et servir des variables enrichies recréerait un décalage entraînement/utilisation. L’Elo, les statistiques driver/entraîneur et tandem nécessitent des résultats de courses complets et ne sont pas artificiellement reconstruits à partir d’un seul cheval.

Le contrôle individuel de la PR permet désormais de conserver les données enrichies lors des prochaines demandes de prédiction. Les vecteurs initiaux et les corrections horodatées doivent être évalués ensemble, avec toutes les courses admissibles et leurs résultats, avant de choisir une nouvelle calibration. Aucun seuil de rentabilité ni nouvelle probabilité validée n’est inventé.

Validation : replay réel exécuté, 196 tests sans échec, 5 ignorés. Les tests vérifient que seuls les cinq champs autorisés changent, qu’un historique manquant ou contradictoire bloque la correction et qu’aucune recommandation n’est émise.
