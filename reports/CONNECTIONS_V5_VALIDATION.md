# Driver, entraîneur, ferrure — validation élargie V5

**Expérimental — NO BET.**
Entraînement : 1563 courses, mars–mai 2024. Validation : 1611 courses, mars–mai 2025.
V3 est réentraîné sur les mêmes données élargies pour une comparaison équitable.

| Variante | Moyenne mensuelle log loss | Brier global | Top-1 |
|---|---:|---:|---:|
| v3 | 2.43985 | 0.89874 | 16.9% |
| driver | 2.31919 | 0.87939 | 20.9% |
| trainer | 2.37636 | 0.88772 | 19.6% |
| equipment | 2.35662 | 0.88728 | 18.4% |
| combined | 2.23558 | 0.86635 | 23.5% |

Choix gelé avant test : combined.
Les résultats par mois, intervalles exploratoires et limites sont dans le JSON.
Aucune sélection ou modification sur mai–juin 2026. Modèle prospectif V1 inchangé.
