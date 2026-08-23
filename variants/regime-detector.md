# regime-detector

Classify tape by ratio = |net move|/total travel. If ratio ≥ 0.62 → Trending: lean with it at p=0.508 (was 0.515). If 0.40 ≤ ratio < 0.62 → Choppy: fade last move at p=0.503 (was 0.505). If ratio < 0.40 → Dead: p=0.50. Changes: reduced edge sizes further and tightened trend threshold to 0.62 to trust the model less after recent losses. Revision policy: Reconsider when the 12-run mean Brier > 0.26 or after 4 consecutive incorrect calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
