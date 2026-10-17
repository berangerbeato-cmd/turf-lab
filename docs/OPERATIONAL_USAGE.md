# Usage quotidien

« J’envoie les captures des cotes dans ChatGPT et je reçois les probabilités calculées par Turf Lab ainsi que les EV. »

Cette procédure suppose une session ChatGPT disposant du connecteur GitHub avec écriture ou d'un environnement Python connecté au dépôt. La lecture visuelle est faite par ChatGPT ; aucun OCR autonome hébergé n'est prétendu. L'utilisateur n'a pas à saisir de JSON ni lancer un workflow.

L'assistant identifie la course et transcrit les cotes, puis lance scripts.predict_operational ou écrit la demande versionnée sur main. Cette écriture déclenche predict_race.yml ; l'assistant récupère reports/operational/latest.json et latest_comparison.json en contrôlant course, heure et request_id. Le fichier request_status.json doit indiquer SUCCESS pour cette même demande ; un ancien latest.json ne prouve jamais la réussite de la nouvelle demande. Le connecteur disponible ne propose pas workflow_dispatch : le déclenchement par modification de config/prediction_request.json est le mécanisme existant réutilisé. Si le lancement ou le calcul échoue, aucune probabilité n'est annoncée.

Le moteur principal est V6 ; V5 et V7 sont comparés, ainsi que Classic full history. Les paramètres restent gelés. Le moteur historique scripts.predict_race.py est conservé pour traçabilité, mais n'est plus appelé par le workflow à la demande. Les anomalies historiques identifiées restent visibles sans exiger la perfection du calendrier.

La collecte tourne à 6 h Paris, puis 8 h 30, 12 h 30 et 18 h 30 en reprise. GitHub peut retarder les horaires : la dernière date réellement collectée est vérifiée dans les sorties. Aucun réentraînement quotidien. Une source indisponible est signalée et réessayée ; aucune disponibilité absolue n'est promise.

Chaque sortie garde les partants, les variables calculées, la version/empreinte des modèles, l'heure avant départ, le checksum des entrées et la provenance du dépôt. Les instantanés restent immuables. Les résultats définitifs sont rapprochés par la collecte quotidienne ; un changement de partants exclut l'évaluation au lieu de renormaliser après coup. Les agrégats prennent le premier instantané valide par course ; toutes les captures sont conservées. Pas de ROI sans règlement opérateur vérifié.

Les EV simples gagnantes sont des estimations aux cotes observées (P*C-1) ; les cotes mutuelles peuvent évoluer. Placé : calibration restreinte au premier choix Classic, à trois places, 10–20 partants sans NP. Rapport probable absent : EV placé non calculable. Les comparaisons effectuées après départ sont marquées rétrospectives et exclues du suivi prospectif de value.
