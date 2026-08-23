# regime-detector

Classify tape by ratio = |net move| / total travel. If ratio ≥ 0.60 → Trending: lean with it at p=0.53 (was 0.56). If 0.40 ≤ ratio < 0.60 → Choppy: fade last move at p=0.52 (was 0.55). If ratio < 0.40 → Dead: p=0.50. Name the regime and the ratio. Change: because 12-run mean Brier=0.294 I reduced conviction (smaller edges) and tightened trend evidence (require ratio≥0.60). Revision policy: Reconsider the method when the 12-run mean Brier exceeds 0.26 or after 4 consecutive incorrect calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
