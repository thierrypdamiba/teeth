# round-number

Short-horizon forecaster: price gravitates to round numbers (thousands, 500s). If the strike sits just below an approaching round, lean that it will hold as resistance; just above, support. No round in play → 0.50. Usual maximum lean up to p=0.58; never exceed p=0.62. Change: mean Brier 0.244 ≤ 0.25 so I restore full leans this round (do not halve deviations). Revision policy: reassess every 12 resolved rounds; restore full leans if mean Brier ≤ 0.25, keep reduced leans while mean Brier > 0.25.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
