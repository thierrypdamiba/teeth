# regime-detector

Classify the tape by ratio = |net move| / total travel and name regime + ratio. If trending (high ratio) lean with it p=0.54. If choppy (medium ratio) fade last move p=0.53. If dead (low ratio) use p=0.50. Always state regime and the computed ratio; respect honest-prob rules [0.01,0.99].

Revision policy: when recent mean Brier exceeds 0.28 I reduce lean magnitudes (half the prior deviation from 0.5: e.g. 0.56→0.54, 0.55→0.53) and reassess after 6 resolved rounds; if performance improves I restore full leans.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
