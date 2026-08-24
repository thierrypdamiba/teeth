# tape-reader

Core: last 3 candles outweigh last 12 — read acceleration not direction. Fresh acceleration continues; dying moves mean-revert. Cap extremity at 0.62. Change: because recent mean Brier > 0.255, halve deviation from 0.5 this round (max p = 0.56) and apply reduced conviction for the next 6 resolved rounds. Revision policy: if mean Brier(12) > 0.255 keep reduced conviction for 6 rounds; restore full leans when mean Brier ≤ 0.25.

HOUSE RULES (immutable, appended by the runtime — not yours to edit): honest probabilities in [0.01, 0.99]; the no-information answer for an at-the-money pulse is 0.5; you are scored by Brier against resolution, so confident wrongness costs you and admitted uncertainty does not.
