# Opposition et risque de faute — validation V3

**Validation seulement ; aucun test indépendant ni déploiement. NO BET.**

Entraînement : 496 courses de mars 2024. Validation : 537 courses de mars 2025.

| Modèle | Log loss | Brier | Premier choix gagnant |
|---|---:|---:|---:|
| baseline | 2.43689 | 0.89973 | 18.1% |
| opposition | 2.42485 | 0.89809 | 19.9% |
| dq | 2.43687 | 0.89988 | 18.8% |
| combined | 2.42387 | 0.89815 | 19.2% |

Écarts de log loss à la référence : négatif = amélioration. Intervalles exploratoires par rééchantillonnage des journées.
- opposition : -0.01204, intervalle 95 % [-0.022745325302708376, -0.0013468842391653152].
- dq : -0.00002, intervalle 95 % [-0.0018200609114600798, 0.0016833248412827576].
- combined : -0.01302, intervalle 95 % [-0.023026215642849606, -0.0027953842606063127].

Pas de nouveauté mathématique revendiquée : Elo et régularisation sont des références établies.
DQ et rangs inconnus exclus des duels Elo ; NP exclus de toutes les mises à jour.
Mises à jour après chaque journée uniquement. Notes réinitialisées chaque année pour ne pas inventer les mois non observés.
Le test V2 de mars 2026 n’a pas été chargé. Une nouvelle période indépendante est nécessaire avant toute validation finale.
