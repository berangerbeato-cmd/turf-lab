# Diagnostic et décision

## Conclusion

Les grosses EV ne constituent pas un avantage démontré. Les probabilités sont
insuffisamment discriminantes face au marché : les favoris sont sous-estimés et
les outsiders surestimés. Le biais apparaît sur les deux modèles figés, sur des
milliers de courses, et subsiste avec les cotes PMU DIRECT et REFERENCE analysées
séparément. Ce constat ne repose pas sur la seule perte du 29 octobre.

Les tableaux ne sont pas des prévisions recalibrées. Les probabilités historiques
et les paramètres restent intacts. Le marché normalisé est un comparateur et non
une vérité individuelle. L'analyse rétrospective ne permet pas de calculer un ROI
réalisable à partir de captures ZEturf avant départ.

## Ce qui a été réellement exécuté

- 4 661 prédictions Classic reproduites à partir des vecteurs figés : erreur
  maximale 1,11 × 10^-16. Empreintes du modèle, des données et des sorties vérifiées.
- Audit V6 sur ses 2 175 prédictions figées de juillet–octobre 2025 ; vérification
  des dépendances figées et des manifestes sources. Pas de nouveau test vierge.
- Jointure par course et numéro ; identité et résultat contrôlés contre les
  vecteurs Classic ; DQ conservées comme perdantes, NP exclus, courses à prix
  incomplets exclues entièrement. Aucune imputation de cote manquante.
- Cotes DIRECT : 4 346 courses Classic et 2 043 V6 exploitables. Les 315 et
  132 autres sont listées dans le JSON. Cotes REFERENCE : 3 452 et 1 519 courses.
- Ventilation par cote, âge, sélection EV positive et EV >= 100 %. Pour Classic :
  également nombre de sorties récentes, taux de DQ passé et cote × couverture.
- Intervalles descriptifs par rééchantillonnage des journées (400 répétitions,
  graine fixée), uniquement si au moins 100 partants et 30 journées ; ni test
  multiple corrigé ni indépendance des chevaux entre journées supposée.
- Aucune collecte réseau, aucun entraînement, aucun remplacement des archives.

## Pourquoi l'audit global de calibration masquait le problème

Classic conserve des moyennes annoncées proches des fréquences observées si l'on
regroupe uniquement par quantité d'historique. Mais dans chacun de ces groupes,
les sélections EV positive sont trop optimistes :

| Sorties récentes utilisées | Sélections EV > 0 | Probabilité moyenne | Victoires observées |
|---|---:|---:|---:|
| 0 | 7 968 | 5,75 % | 2,48 % |
| 1 | 8 456 | 8,20 % | 4,30 % |
| 2–3 | 11 338 | 9,13 % | 4,78 % |
| 4–5 | 1 334 | 8,51 % | 4,35 % |

Ainsi, éliminer seulement les chevaux avec peu d'historique ne résout pas le biais.
L'EV trie sur le produit probabilité × cote : elle retient les erreurs optimistes
quand le modèle attribue trop de masse aux outsiders. La calibration de toutes
les prédictions ne valide pas celle du sous-ensemble sélectionné par EV.

## Disqualifications

Les DQ sont présentes dans les variables et dans la cible perdante. Leur taux
observé dans Classic augmente de 6,64 % pour une variable de DQ passée < 10 % à
35,59 % pour une variable >= 30 %. Ce signal discrimine donc effectivement une
partie du risque. Il s'agit d'un indicateur historique régularisé, pas d'une
probabilité de DQ spécialement calibrée.

Le taux de DQ observé reste voisin de 21–22 % dans les tranches de cotes 10–20,
20–50, 50–80 et 80+, alors que la surestimation relative des victoires augmente
fortement. Les disqualifications ne suffisent pas à expliquer toute la dérive.
L'Elo ne se met à jour qu'entre chevaux classés : ce choix laisse aux autres
variables la prise en compte des fautes. Son efficacité devra être testée par
ablation dans un nouveau protocole, sans changer les coefficients après coup.

## R4C8 : historique individuel et score

Les probabilités V6 et Classic du fichier exact de la R4C8 ont été reproduites
avec une erreur nulle. La formule EV n'est pas en cause.

Sur les 12 pouliches, six ont zéro sortie utilisée dans la fenêtre de forme de
60 jours, et six une seule. Le champ `musique` du snapshot avant départ expose
pourtant davantage de performances. Il n'est pas une entrée du moteur figé.

La recherche par nom dans les **5 161 courses vérifiées du 1er janvier au
28 octobre 2026** ne retrouve aucune course de Nativa Bella. Le snapshot indique
une course et une victoire. Ce n'est donc pas seulement une course trop ancienne
qui aurait été coupée par la fenêtre de 60 jours, dans cette archive 2026.
L'origine précise de l'absence reste non résolue : couverture hors périmètre
PMU, identité différente ou donnée source manquante. Ne pas inventer la date ni
la course de cette victoire et ne pas injecter une « 1a » sans provenance datée.

Naranja d'Avran a trois courses retrouvées (19 août, 28 août, 21 septembre), dont
une seule dans les 60 jours. Le snapshot affiche `Da1a5a4a8a` : la faute plus
récente que la victoire du 21 septembre n'est pas retrouvée dans ces enregistrements.
Le modèle ne dispose donc pas de toute l'information récente visible au marché.

Pour le n° 10 contre le n° 2, la contribution du bloc « forme récente + valeurs
manquantes » au différentiel de score est +0,721 pour V6 et +0,830 pour Classic.
Les autres variables, réunies, favorisent au contraire le n° 2 (−0,405 et −0,242).
Le traitement de cette forme inégale suffit donc à inverser leur ordre dans
les modèles. C'est une décomposition exacte du score, pas une preuve causale
ni une probabilité corrigée.

## Corrections livrées

- Suspension explicite dans `config/recommendation_policy.json`, README et AGENTS.
- Chaque nouvelle prédiction et comparaison affiche
  `recommendations_allowed: false` et `recommendation_status: SUSPENDED`.
- Politique absente, corrompue ou tentative d'activation non prévue : maintien
  de la suspension. Une EV élevée ne réactive rien.
- Calculs de recherche conservés, aucun poids ni source figée modifiés.
- Script d'audit reproductible et tests des jointures, DQ, NP, tranches, marchés
  incomplets et suspension malgré une EV extrême.

## Conditions avant toute reprise

1. Réconcilier les historiques manquants au niveau cheval, avec dates et identités,
   et distinguer la complétude du périmètre collecté de celle de la carrière.
2. Définir une nouvelle expérience : baseline marché, éventuelle calibration
   conditionnelle au marché, traitement de la forme peu fournie et des DQ.
   Conserver le modèle sportif sans cotes comme comparateur. Aucun coefficient
   correcteur choisi sur les résultats présentés ici.
3. Ajuster sur une période de développement, vérifier sur une période chronologique
   distincte puis en observation prospective. Les historiques déjà inspectés
   ne redeviennent pas un test indépendant.
4. Évaluer les sélections réellement définies à l'avance, avec cotes avant départ
   horodatées, changements de partants et règlements opérateur documentés.
5. Décider explicitement d'une reprise. D'ici là, aucun cheval ni montant conseillé.

## Validation logicielle

Suite complète : **183 tests, aucun échec, 5 tests ignorés**. Les sorties figées
sont conservées ; le garde-fou ne change pas les probabilités. L'audit statistique
s'est exécuté jusqu'au bout. L'avantage économique reste non démontré.
