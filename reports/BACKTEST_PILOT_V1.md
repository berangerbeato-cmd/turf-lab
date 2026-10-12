# Pilote V1 — backtest chronologique

**Statut : expérimental, NO BET.**

Entraînement : 14 courses de 2024. Validation : 12 courses de 2025. Test : 14 courses du 05/10/2026.
Sur 46 courses candidates, 6 sont explicitement mises en quarantaine pour données absentes ou ambiguës. La liste et les causes sont dans le JSON ; l'échantillon n'est pas représentatif de toutes les courses.
La sélection utilise seulement la log loss de validation. Le modèle retenu reste inchangé sur le test.

| Modèle, test uniquement | Log loss | Brier multiclasses | Favori correct |
|---|---:|---:|---:|
| Retenu (logit) | 2.4845 | 0.8960 | 7.1% |
| Uniforme | 2.6444 | 0.9282 | 7.1% |

Brier = somme des erreurs quadratiques des partants, puis moyenne par course. Les égalités de probabilité sont départagées par numéro croissant : le top-1 uniforme dépend donc de cette convention.

Calibration, effectifs et sous-groupes figurent dans backtest_pilot_v1.json. L’ablation mesure la variation de log loss de validation lorsqu’une variable est retirée (positif : retrait défavorable).

Un seul jour de test ne permet pas d’estimer une généralisation fiable ni un intervalle de confiance entre journées. Les résultats sont exploratoires. Aucun Elo/arbre ajouté sur cet échantillon trop faible.

Les résultats historiques sont datés avant la cible ; leur disponibilité réelle au moment du départ ancien n’est pas prouvée. Une validation prospective reste nécessaire. Aucun ROI calculé.
