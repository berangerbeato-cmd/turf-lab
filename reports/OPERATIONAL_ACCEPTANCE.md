# Vérification opérationnelle — 17 octobre 2026

Les changements de reprise sont intégrés à main (PR #2, merge 960a131f6da2a33ceb8cdb2aa1046152d508f772). Aucun réentraînement ni modification des paramètres gelés. V1 reste archivé et ne sert plus de moteur au workflow manuel.

## Preuves réelles

- Prédiction GitHub Actions 38957564560 : SUCCESS. Enghien 2026-10-17 R5C1, 14 partantes ; V5, V6, V7 et Classic full réellement calculés le 16 octobre à 19:53:15 UTC avant le départ prévu le 17 à 14:07 UTC. Résultat récupéré depuis ChatGPT.
- Collecte quotidienne 39001849526 : SUCCESS. Rapport du 17 octobre 04:17:10 UTC : 30 481 courses vérifiées, 15 récupérées, dernière journée complète 2026-10-16 = J-1. Six journées anciennes incomplètes, une journée de programme inconnue et 21 courses connues manquantes restent tracées ; pas de blocage général.
- Captures ZEturf du 16 octobre : 13 cotes transcrites et rapprochées des partants de Vincennes R1C3. Comparaison exécutée contre les prédictions V6/V7 archivées avant le départ. Ce rejeu effectué après la course est explicitement rétrospectif : aucune prétention de sélection value prospective.
- Suite locale : 176 tests, succès, cinq tests optionnels ignorés. La vérification GitHub a révélé les dépendances NumPy puis SciPy manquantes dans deux workflows historiques de suivi ; versions explicites ajoutées, sans entraînement. Les workflows corrigés de cohorte 39011041233 et de suivi V5/V6/V7 39011041172 sont ensuite terminés avec SUCCESS.

## Choix et périmètre

V6 reste référence ; V5, V7 et Classic full sont comparateurs. XGBoost et ensembles restent archivés : pas de promotion sur version ou performance exploratoire. Voir OPERATIONAL_MODEL_AUDIT.md pour les périodes distinctes et les métriques, et operational/model_files.json pour les variantes et empreintes.

Chaque demande a un request_id et un état persistant ; un ancien latest.json ne constitue pas la réussite d'une nouvelle demande. Vérifier request_status.json = SUCCESS et le même identifiant. Les sorties conservent les entrées, variables, empreintes, horodatage et historique utilisé. Les non-partants imposent une nouvelle vérification avant interprétation des cotes.

L'EV gagnant est P*C-1 à la cote décimale totale observée ; l'implicite 1/C reste séparé du modèle. Le placé est limité au premier choix Classic, 10–20 partants sans NP, trois places rémunérées confirmées : aucune extrapolation aux autres chevaux. Sans rapport probable pré-course vérifié : EV placé non calculable.

## Usage et limites restantes

L'utilisateur envoie ses captures dans une session ChatGPT connectée à GitHub avec écriture, ou disposant du runtime adapté. L'assistant lit les cotes, écrit la demande, suit le workflow puis récupère les résultats. Aucun déclenchement GitHub ni JSON à saisir par l'utilisateur. Le connecteur n'expose pas workflow_dispatch ; la modification versionnée du fichier de demande est le déclencheur testé.

Aucune cote actuelle de la course de test du 17 octobre n'a été fournie : pas d'EV actuelle inventée. La chaîne en ligne avec une nouvelle capture sera vérifiée à sa réception. Les captures historiques prouvent le rapprochement et le calcul EV, séparément du test réel sur course future. Pas de garantie de disponibilité GitHub/source, de calibration universelle ou de rentabilité. Les résultats prospectifs de la nouvelle chaîne restent à accumuler ; aucun pari réel automatique.

## Recalcul du 17 octobre validé

Workflow 39011139390 : SUCCESS. Demande operational-e2e-20261017-refresh, état et résultat récupérés par ChatGPT avec identifiants concordants. Calcul 2026-10-17T06:48:24.272217+00:00 (08:48 Paris), départ prévu 16:07 Paris ; historique jusqu'au 16 octobre. Quatorze probabilités finies par modèle, somme 1 à la précision numérique.

Versions : v5@f537cc13991e, v6@fb2aea565cfb, v7@97f565c8f0e2, classic_full@1c5e0e8f4900.

| N° | Cheval | P V5 | P V6 principale | P V7 | P Classic |
|---:|---|---:|---:|---:|---:|
| 1 | LA LA LAND | 7.62 % | 7.08 % | 5.51 % | 8.51 % |
| 2 | LUCIA DU CHATELET | 2.04 % | 2.27 % | 1.93 % | 2.68 % |
| 3 | LADY MAJOR | 3.12 % | 3.32 % | 2.00 % | 4.26 % |
| 4 | L'ELITE DU CHOQUEL | 10.41 % | 9.96 % | 7.00 % | 8.78 % |
| 5 | LADY BOSSE | 6.35 % | 6.52 % | 6.70 % | 6.33 % |
| 6 | LILY ROSE MYSTIC | 4.11 % | 4.04 % | 4.15 % | 3.45 % |
| 7 | LINE MAJYC | 6.96 % | 7.39 % | 5.47 % | 8.85 % |
| 8 | LEELY DE BLARY | 5.28 % | 5.31 % | 10.40 % | 4.54 % |
| 9 | LOKA LOKA | 35.19 % | 35.06 % | 34.08 % | 35.94 % |
| 10 | LILYROSE WIND | 4.30 % | 4.25 % | 7.82 % | 4.07 % |
| 11 | LUNE DU DOUET | 6.41 % | 5.84 % | 6.34 % | 3.95 % |
| 12 | LOVELY GODIVA | 2.45 % | 2.59 % | 1.75 % | 2.30 % |
| 13 | LADY ANGELE | 2.08 % | 2.24 % | 2.05 % | 2.12 % |
| 14 | LADY DU VALLON | 3.68 % | 4.13 % | 4.80 % | 4.22 % |

Aucune cote actuelle fournie : EV gagnant actuelle non calculable. Placement du n°9 Classic : 59.99 % dans le périmètre calibré décrit, sous confirmation opérateur des trois places payées ; EV placé non calculable sans rapport probable pré-course. La capture de partants doit être recontrôlée lors de l'envoi des cotes.
