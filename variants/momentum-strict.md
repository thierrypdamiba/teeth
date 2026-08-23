# momentum-strict

Momentum-only: if the last three closes all move the same direction I back the move; mixed bars → p=0.50. Change: because my 12-run mean Brier=0.251 (underperforming) I reduce the edge to p=0.57 when the 3-bar rule fires (was 0.60). Revision policy: Reconsider and shrink further when the 12-run mean Brier exceeds 0.255 or after 4 consecutive incorrect momentum calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
