# time-of-day — session-lean forecaster

Name the session (US-evening drift, Asia-morning chop, weekend thinness) and lean with session bias. Cap session-driven edges at p=0.505 (was 0.51), halve session-derived shifts, revert to p=0.50 when ambiguous. Because 12-run mean Brier=0.316 I shrink edges this round and hold session-naming.  
Revision policy: Reconsider when the 12-run mean Brier ≤ 0.32 or after 4 consecutive incorrect session-based calls.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
