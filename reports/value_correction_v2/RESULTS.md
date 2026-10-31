# Correction de la value — modèle de base V3

Ajustement sur 3426 courses de 2025 ; évaluation sur 2578 courses de 2026 déjà examinées.
La version hybride utilise explicitement les cotes. Aucun changement du modèle sportif actif, aucun ROI.

| Modèle | Log loss ↓ | Brier ↓ | Victoires prévues parmi EV positives | Observées |
|---|---:|---:|---:|---:|
| sport | 2.108413 | 0.843176 | 1360.7 | 784 |
| market_normalized | 1.941194 | 0.802075 | 0.0 | 0 |
| market_calibrated | 1.936756 | 0.804325 | 0.9 | 0 |
| hybrid | 1.924891 | 0.802717 | 475.4 | 452 |

Poids hybride [marché, sport] : [0.9645548573806333, 0.24742426735604].

Les groupes EV positives diffèrent selon les modèles : comparer leur calibration, pas seulement leur nombre de victoires.
Prix PMU de référence archivés ; pas de prix ZEturf exécutable ni de rapports payés. Les cotes finales peuvent changer.
Le bilan face au marché calibré figure dans evaluation.json. Pas de sélection de seuil sur le test ni de promotion automatique.
