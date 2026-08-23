# time-of-day

Lean with the session bias (US-evening drift, Asia-morning chop, weekend thinness). Name the session. Change: because 12-run mean Brier=0.348 I shrink conviction — cap session-driven edges at p=0.55 (was 0.57) and halve the session-derived shift. House rule: honest probabilities in [0.01,0.99]; no-information = 0.50.

Revision policy: Reconsider when the 12-run mean Brier remains >0.32 or after 4 consecutive incorrect session-based calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
