# Rapprochement des historiques — Beaumont 15 novembre 2026

## Correction du diagnostic
Les deux disqualifications du n°10 (11 et 21 octobre) étaient déjà présentes. Le contrôle confondait TOULOUSE et LA CEPIERE. Les alias documentés et la ponctuation sont désormais normalisés ; date et numéro de course restent obligatoires.
Les alertes sur la fenêtre de 60 jours passent de 11 à 4 chevaux : 2, 7, 9, 11. Les autres étaient de faux positifs.

## Enrichissement isolé et effet mesuré
378 départs antérieurs supplémentaires dans les historiques individuels archivés avant course ont été rapprochés des archives. Cela inclut des départs anciens, hors fenêtre de 60 jours. Les neuf variables originales last5/DQ20 ont été reproduites avant toute correction.
Seules la forme sur cinq sorties et les quatre variables DQ20 sont recalculées. Elo, driver, entraîneur et tandem restent inchangés : il s’agit d’une sensibilité partielle, pas d’un modèle corrigé intégralement ou validé. Aucune prédiction ancienne ni aucun poids modifié.

| N° | V3 original | Sensibilité enrichie |
|---|---:|---:|
| 2 | 2.03 % | 1.98 % |
| 3 | 9.82 % | 9.77 % |
| 4 | 5.51 % | 5.56 % |
| 5 | 32.02 % | 30.50 % |
| 6 | 3.16 % | 2.96 % |
| 7 | 1.16 % | 1.17 % |
| 8 | 13.38 % | 13.50 % |
| 9 | 10.16 % | 11.04 % |
| 10 | 6.33 % | 6.38 % |
| 11 | 5.12 % | 5.56 % |
| 12 | 2.85 % | 2.83 % |
| 14 | 3.22 % | 3.25 % |
| 15 | 1.85 % | 1.87 % |
| 16 | 3.40 % | 3.64 % |

Le premier choix reste le 5. Sa probabilité passe de 32,02 % à 30,50 % ; à la cote capturée de 3,5, l’EV théorique passe de +12,06 % à +6,74 %. Ce passage sous le seuil illustre la sensibilité du filtre, sans démontrer que la nouvelle estimation est meilleure.
Les résultats de la course cible ne sont pas utilisés dans le recalcul. Cette expérience rétrospective est exclue du comparatif prospectif.
Reproduction : `python -m scripts.reconcile_beaumont_history`. Sources et différences : diagnostic.json et sensitivity.json.
