# Placement and pair-market study

Decision date: 2026-10-15. Research only, no orders, no promotion of the current model.

## Scope

Compare simple win, simple place (top3), jumelé placé (both top3), and ZE2/4
(both top4) on identical races. Start with exact Plackett-Luce unordered-set
probabilities from frozen winner predictions. This is a hypothesis, not a claim
that winning strengths identify placement strengths. Disqualifications and pace
can invalidate that hypothesis.

For the first common-cohort experiment require 10–20 runners, no non-runners,
and unambiguous top-four arrival agreeing with participant ranks. Preserve and
count every exclusion. Do not change archived inputs or original models.

Compare classic, XGBoost, ensemble and uniform probability baselines. Binary
Brier/log loss are comparable within a market, not across differing base rates.
Highest-probability selections are diagnostic tickets, not value picks.

Observed overconfidence motivates a separate monotone logistic calibration on
2025 ONLY, for each classic maximum-probability selected ticket. Fixed ridge .001;
no hyperparameter search on 2026. Freeze parameters before reading test outcomes.
Calibration does not apply to arbitrary combinations or tickets chosen by EV.
Report 2026 selected-ticket calibration, seasons and week-blocked intervals.
The reused holdout is exploratory: future prospective testing remains required.

## Pricing evidence and blockers

Official rules: https://www.zeturf.fr/fr/document/4
Public example with final payouts: https://www.zeturf.fr/fr/course-du-jour/2026-07-17/R1C4-cabourg-grand-prix-de-la-ville-de-cabourg
Observed public archives show final winning dividends. A public example is not
an established historical dataset or proof that probable prices were available
before the race. Do not substitute PMU dividends for ZEturf dividends.

No pre-race ZEturf quote dataset is established in this study. Therefore EV,
ROI, bank drawdown, economic optimality and profitability remain UNVALIDATED.
The reciprocal of a model probability is only a model-derived break-even total
return. The 1.05/p column is an illustrative 5% scenario, not a betting rule.

For a future quote record require operator, race ID, market, normalized selection,
source URL/evidence hash, observed-at UTC, independently verified race-start UTC,
quote kind (probable/final), return basis and unit stake, low/high quoted return,
and whether the dividend includes stake. Store final settlement separately.
Reject quotes dated at/after departure for selection. Unknown time means NO BET.
Preserve probable ranges; do not present midpoint values as guaranteed prices.

## Risk/value comparison once data exists

Freeze selection rules before outcomes; compare equal daily total outlay,
including all losing tickets and the full cost of combinations. Include fees in
paid dividends, no double subtraction. Simulate one-euro tickets, no martingale.
Report net ROI with day/week intervals, loss frequency, longest losing run,
maximum drawdown, correlated same-race exposure and sensitivity to late payout
changes. A prize payment can still be below the total cost of the ticket bundle.
Do not select the best market on the same sample used to claim its performance.
