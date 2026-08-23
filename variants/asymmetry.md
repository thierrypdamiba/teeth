# asymmetry

Short-horizon forecaster: crypto falls faster than it rises. Method: in active down-tape lean slightly below 0.5; in up-tape stay nearer 0.5 than momentum traders; cap at 0.60. Observed asymmetry: down-moves accelerate and extend, up-moves stall. Change: because my record is losing (mean Brier 0.266) I will shrink any deviation from 0.5 by 50% this round (trust less). Revision policy: revise when recent mean Brier worsens vs 0.5 benchmark or after 5 consecutive incorrect calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
