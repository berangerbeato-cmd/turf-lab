# Usage quotidien

« J’envoie les captures des cotes dans ChatGPT et je reçois les probabilités calculées par Turf Lab ainsi que les EV. »

Cette procédure suppose une session ChatGPT disposant du connecteur GitHub avec écriture ou d'un environnement Python connecté au dépôt. La lecture visuelle est faite par ChatGPT ; aucun OCR autonome hébergé n'est prétendu. L'utilisateur n'a pas à saisir de JSON ni lancer un workflow.

L'assistant identifie la course et transcrit les cotes, puis lance scripts.predict_operational ou écrit la demande versionnée sur main. Cette écriture déclenche predict_race.yml ; l'assistant récupère reports/operational/latest.json et latest_comparison.json en contrôlant course, heure et request_id. Le fichier request_status.json doit indiquer SUCCESS pour cette même demande ; un ancien latest.json ne prouve jamais la réussite de la nouvelle demande. Le connecteur disponible ne propose pas workflow_dispatch : le déclenchement par modification de config/prediction_request.json est le mécanisme existant réutilisé. Si le lancement ou le calcul échoue, aucune probabilité n'est annoncée.

Le modèle sportif principal est désormais **Available History V3** (`available_history_v3`), avec V6 et Classic full en comparateurs. V5 et V7 restent archivés. La table quotidienne compare au minimum les cotes, les probabilités et l'EV du modèle principal, avec V6/Classic en contrôle. Paramètres sportifs gelés et aucune réentraînement. Le moteur historique scripts.predict_race.py est conservé pour traçabilité mais n'est plus appelé par le workflow à la demande.

La collecte tourne à 6 h Paris, puis 8 h 30, 12 h 30 et 18 h 30 en reprise. GitHub peut retarder les horaires : la dernière date réellement collectée est vérifiée dans les sorties. Aucun réentraînement quotidien. Une source indisponible est signalée et réessayée ; aucune disponibilité absolue n'est promise.

Chaque sortie garde les partants, les variables calculées, la version/empreinte des modèles, l'heure avant départ, le checksum des entrées et la provenance du dépôt. Les instantanés restent immuables. Les résultats définitifs sont rapprochés par la collecte quotidienne ; un changement de partants exclut l'évaluation au lieu de renormaliser après coup. Les agrégats prennent le premier instantané valide par course ; toutes les captures sont conservées. Pas de ROI sans règlement opérateur vérifié.

Les EV simples gagnantes sont des estimations aux cotes observées (P*C-1) ; les cotes mutuelles peuvent évoluer. Placé : calibration restreinte au premier choix Classic, à trois places, 10–20 partants sans NP. Rapport probable absent : EV placé non calculable. Les comparaisons effectuées après départ sont marquées rétrospectives et exclues du suivi prospectif de value.


## Stratégie quotidienne de tickets (à partir du 16 novembre 2026)

Règle enregistrée dans `config/daily_ticket_strategy_v1.json`, calculée par `turf_lab/daily_ticket.py` et enregistrée lors du workflow de prédiction dans `reports/operational/latest_ticket.json` et le dossier horodaté `predictions_operational`.

- **Simples gagnants (SG)** : classer les partants sur leur probabilité de victoire **Available History V3**. Dans les **quatre premiers**, retenir uniquement les chevaux dont l'**EV SG estimée est au moins +10 %**, calculée sur la cote ZEturf fournie. Afficher aussi séparément ce que retiendrait le filtre **top 3 + EV ≥ 10 %**. Si aucun cheval n'est éligible, le ticket SG est vide ; la mise SG n'est pas fixée par le protocole.
- **ZE5 systématique à 1 €** : proposer exactement les **cinq premiers du même classement V3**, en **ZE5 désordre**, **une seule combinaison à 1 € au total** et sans multiplier les chevaux. **Seulement si ZEturf propose le ZE5 sur cette course** ; sinon signaler l'absence d'offre. Une capture de cotes n'établit pas l'offre ZE5.
- **Différence des objectifs** : le filtre EV s'applique aux SG, pas au ZE5. Le ZE5 est une combinaison des cinq probabilités de **victoire** les plus élevées, **pas** la sortie d'un modèle calibré de classement top 5. Ne pas le présenter comme une probabilité fiable de quinté.
- **Moment** : les cotes observées plus de quinze minutes avant le départ peuvent servir à préparer le ticket de recherche, horodaté correctement. Elles **ne comptent pas** dans le suivi prospectif SG J−15 figé, sauf capture admissible ultérieure. Ne jamais modifier l'horodatage pour rendre une capture éligible.
- **Statut** : plan de **simulation / recherche**, pas de pari automatique ni de promesse de rentabilité. Vérifier les partants, les cotes et l'offre ZE5 ; enregistrer les sommes effectivement engagées et les retours uniquement si prouvés. Ne pas confondre ticket suggéré et ticket réellement validé par l'opérateur.

La comparaison de performance prospective SG top 3/top 4 reste gouvernée séparément par `config/sg_ev_probability_comparison_v1.json`, sans modifier rétroactivement les observations ou la politique de suspension.
