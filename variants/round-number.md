# round-number

Price gravitates to round numbers (thousands, 500s). If the strike sits just below an approaching round, lean that it will hold as resistance; just above, support. No round in play → 0.5. Never exceed 0.62. Because recent scoring is slightly poor, temper conviction: halve the usual deviation from 0.5 this round (e.g. 0.58 → 0.54). Revision policy: reassess after each 12 resolved rounds — restore full leans if mean Brier ≤ 0.25; keep reduced leans while mean Brier > 0.25.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
