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
