# Décision — correction expérimentale

La correction a été ajustée sur 3 426 courses de 2025 puis évaluée sur 2 578 courses de 2026. Les prix de référence doivent être antérieurs au départ, complets, sans non-partant ni somme des inverses des cotes inférieure à 1. Le premier essai sans ces contrôles de cohérence reste archivé dans initial_before_field_integrity_check. La modification porte sur la qualité des données, pas sur un réglage de coefficients en fonction des résultats 2026.

Le nouveau modèle utilise explicitement le marché. Il améliore la log loss (1,92352 contre 2,11508 pour Classic, 1,94119 pour le marché normalisé). Le Brier reste légèrement moins bon que celui du marché normalisé (0,80217 contre 0,80208). La calibration reste insuffisante aux extrêmes : favoris <3 à 45,78 % contre 40,74 % observés ; cotes >=80 à 0,50 % contre 0,09 %. Ces résultats ne justifient aucune reprise des paris.

Les historiques individuels PMU ont été récupérés pour les douze chevaux du cas R4C8. Dix présentent des performances récentes absentes de la fenêtre utilisée par le modèle. La victoire de Nativa Bella du 18 octobre à Machecoul et la disqualification de Naranja d’Avran du 11 octobre à Challans sont retrouvées, datées et archivées. Les performances du jour cible et futures sont exclues.

Le contrôle individuel est ajouté à la prochaine exécution du moteur opérationnel, sous forme de diagnostic séparé. Les vecteurs et poids V6/Classic ne sont pas modifiés : injecter ces nouvelles variables dans leurs poids figés sans validation serait une autre source d’erreur. Les variables de forme enrichies sont disponibles pour une prochaine expérience avec des données historiques comparables.

Le candidat est accessible uniquement par scripts.predict_market_repair, en recherche. Le replay de la course passée est explicitement étiqueté rétrospectif. Pas de recommandation, pas de mise, pas de rendement annoncé. La transposition de prix PMU de référence à des captures ZEturf n’est pas validée.

Validation : 192 tests exécutés sans échec, dont 5 ignorés ; replay réel exécuté. Prochaine validation nécessaire : observations nouvelles horodatées et calibration des extrêmes sur une période de développement séparée. Aucun déploiement du candidat ni réactivation automatique.
