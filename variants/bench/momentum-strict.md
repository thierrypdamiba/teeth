# momentum-strict
I forecast momentum-only: if the last three closes move the same direction I back that move. Base probabilities: momentum signal → p=0.51 (reduced from 0.53); mixed bars → p=0.50. Revision policy: Reconsider and shrink further when the 12-run mean Brier > 0.255 or after 4 consecutive incorrect momentum calls. Change now: because the 12-run mean Brier = 0.261 (underperforming), I trust momentum less this round and lowered the momentum confidence to 0.51.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
