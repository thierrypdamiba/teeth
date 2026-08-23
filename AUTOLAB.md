# teeth as an Autolab target environment

This board is a standing open problem for autoresearch: a fitness function
that refreshes its own questions, hardens as its population improves, and
cannot be memorized — the answers do not exist at forecast time.

## Point a research agent here

- **Objective:** maximize `earned_cap` for variants you author in `variants/*.md`
  (character files — a method, a voice, a revision policy).
- **Fitness arrives via** `ledger.jsonl`: resolved at-the-money pulses on five
  live markets, ~60 verdicts/hour. Sum of Brier edge vs the 0.5 benchmark is
  the season metric ("calibration P&L").
- **Constraints (the constitution — not editable by any experiment):**
  never modify `teeth/*.py` scoring modules or existing ledger rows; live
  forecasts happen only through `examples/rsi_loop.py` against real prints;
  work on branches; analysis in `experiments/`.
- **The control arm every experiment should run:** select the same variant
  population by any static benchmark you construct, and track whether your
  static-selected champions regress on later live generations while
  reality-selected ones hold — the misevolution measurement.

The reference run: an Autolab research agent has held this objective since
2026-08-23 (`thierry-brise/teeth` on app.autolab.ai).
