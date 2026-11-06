# Classement conditionnel V2 et calibration

Un seul candidat, cinq modèles de choix conditionnel. Apprentissage 2022–2024, températures sur 2025 uniquement. V3 inchangée.
2026 est une comparaison exploratoire déjà consultée, pas une validation indépendante.

| Arrivée | Modèle | Réussites | Attendues | Perte désordre (plus bas = mieux) |
|---|---|---:|---:|---:|
| Top3 | v3 | 238/4574 | 351.1 | 4.8951 |
| Top3 | stage_raw | 223/4574 | 201.4 | 4.8009 |
| Top3 | stage_calibrated | 223/4574 | 214.9 | 4.7993 |
| Top4 | v3 | 115/4574 | 271.7 | 5.8679 |
| Top4 | stage_raw | 135/4574 | 116.4 | 5.6280 |
| Top4 | stage_calibrated | 135/4574 | 127.5 | 5.6264 |
| Top5 | v3 | 79/4574 | 261.1 | 6.5921 |
| Top5 | stage_raw | 101/4574 | 93.4 | 6.1596 |
| Top5 | stage_calibrated | 101/4574 | 99.5 | 6.1603 |

Les probabilités désordre somment toutes les permutations par calcul exact. Les températures corrigent toute la distribution conditionnelle : elles ne multiplient pas des probabilités marginales.
La calibration conserve ici la sélection gloutonne : elle corrige la confiance, sans fabriquer de réussites supplémentaires.
Sélection gloutonne des places, pas recherche de la combinaison désordre optimale. Cohorte avec cinq places uniques connues ; les résultats ambigus sont exclus.
Comparer les Brier uniquement sur le même événement (sélection V3), champ fixed_event_brier. Intervalles hebdomadaires appariés dans evaluation.json.
Pas de promotion automatique, rapports commerciaux, bonus ou rentabilité. Une période future gelée reste nécessaire.
