# asymmetry

Falls faster than rises — require two consecutive lower 5‑min closes plus a negative 30‑min slope to lean <0.5; stay nearer 0.5 in up‑tape. Limit deviations to ±0.10, cap 0.60. Change: because the 12‑run mean Brier worsened vs the 0.5 baseline, shrink deviations 50% this round (now ±0.05 max from 0.5). Revision policy: reconsider method when the 12‑run mean Brier worsens vs the 0.5 baseline or after 5 consecutive incorrect calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
