# Départ et aptitude au parcours — validation V4

**Validation seulement, NO BET.**
496 courses d’entraînement (mars 2024), 537 de validation (mars 2025). Aucun résultat 2026 chargé.

| Variante | Log loss | Brier | Premier choix gagnant |
|---|---:|---:|---:|
| v3 | 2.42387 | 0.89815 | 19.2% |
| departure | 2.42422 | 0.89821 | 19.2% |
| aptitude | 2.42430 | 0.89851 | 17.7% |
| combined | 2.42461 | 0.89857 | 17.5% |

Écarts à V3 (négatif = mieux), intervalles exploratoires par journées :
- departure : 0.00035, intervalle 95 % [8.183579970984705e-05, 0.0006186683740649718].
- aptitude : 0.00042, intervalle 95 % [-0.007959100731076694, 0.008340492141795228].
- combined : 0.00074, intervalle 95 % [-0.007737113844140429, 0.008737013123987775].

Sélection selon le critère gelé : v3.
Les distances négatives non corroborées sont manquantes. Aucune position autostart déduite du numéro.
L’aptitude compare la performance passée aux attentes Elo avant cette course, avec régularisation et une fenêtre de 60 jours.
Le type de départ inconnu reste inconnu. Résultats du même jour exclus.
La validation a été réutilisée pour plusieurs itérations : résultat exploratoire, nécessitant une nouvelle période indépendante.
Mars et avril 2026 ont déjà été observés ; aucun réemploi pour choisir V4. Modèle prospectif inchangé.
