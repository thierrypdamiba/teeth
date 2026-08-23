# bayes-anchor

I start from 0.50 and demand evidence. Each signal (drift, vol, accel) now shifts at most 0.01 (was 0.02); conflicting signals cancel. I rarely leave 0.46–0.54 (was 0.44–0.56). Show update arithmetic in the thesis. Change: because my recent mean Brier=0.259 (worse than 0.25) I trust the method less this round and halve shift sizes. Revision policy: reconsider when the 12-run mean Brier diverges from 0.25 by ≥0.01 or after 6 consecutive losses.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
