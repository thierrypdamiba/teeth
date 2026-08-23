# regime-detector
Classify tape by ratio = |net move|/total travel. If ratio ≥ 0.60 → Trending: lean with it at p=0.515 (was 0.52). If 0.40 ≤ ratio < 0.60 → Choppy: fade last move at p=0.505 (was 0.51). If ratio < 0.40 → Dead: p=0.50. Reduced edge sizes this round because the 12-run mean Brier=0.279; kept the tightened trend threshold at 0.60.

Revision policy: Reconsider when the 12-run mean Brier > 0.26 or after 4 consecutive incorrect calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
