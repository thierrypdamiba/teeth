# teeth

**Evals with teeth: score your agents on the future — live prediction markets they can't game — and pay them in capital.**

Benchmarks saturate. Verifiers get gamed. The 2026 literature has a name for it now — *misevolution*: self-improving harnesses that co-evolve against a static evaluator until the metric means nothing ([Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) grades itself on SWE-bench; [DarwinX](https://arxiv.org/html/2608.07545v1) evolves harnesses against fixed suites; [AlphaEvolve](https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/)'s own authors say the path forward is "more environments with robust evaluation functions").

Here is a robust evaluation function: **the future**.

- **You can't memorize what hasn't happened.** Forecasts are scored by Brier against resolution of live prediction-market questions. No contamination, no leakage, no saturation — the question bank refreshes itself by existing.
- **You can't beat zero, you beat the market.** Every forecast records the market's price `c` at that moment. The baseline travels with the score: an agent's skill is `Brier(market) − Brier(agent)`, not applause for guessing 50/50.
- **Scores have consequences.** Calibration pays out as *earned authority* — a spending cap the agent's track record buys. Unproven agents trade at 25% of their standing cap. Confidently-wrong agents decay back to it. Nothing an agent *says* moves its cap; only what *resolves*.
- **Deny by default.** Unknown agents: refused. Hindsight forecasts on resolved questions: refused. Parrot forecasts (no edge vs the market): refused. Kill switch outranks everything.

Zero dependencies. The ledger is append-only JSONL you can audit with your eyes.

## Quickstart

```python
from teeth import Fund, markets

fund = Fund("ledger.jsonl", min_edge=0.02)
fund.register("iris", standing_cap=1000)

# The market's price is fetched at forecast time — the agent never picks
# its own benchmark.
c = markets.quote("manifold:us-recession-in-2026")
fund.forecast("iris", "manifold:us-recession-in-2026", p=0.12, c=c)

# ...the world decides...
fund.resolve("manifold:us-recession-in-2026", outcome=False)

fund.brier("iris")        # 0.0144 — scored by reality
fund.cap("iris")          # authority, earned (starts at 250 of 1000)
fund.check("iris", 500)   # Decision(allowed=False, reason="over earned authority: ...")
fund.stake("iris", p=0.12, c=0.08)  # Kelly-edge stake inside the earned cap
fund.leaderboard()        # agents ranked by earned capital, market baseline beside them
```

## Use it as a fitness function

Evolving harnesses ([DGM](https://arxiv.org/abs/2505.22954)-style or otherwise)? Replace the benchmark:

1. Each variant forecasts the same live question set (Manifold/Polymarket adapters included, stdlib only).
2. Wait for resolution. This is the feature, not the bug: **fitness arrives on the world's clock, so the optimizer cannot query the oracle faster than reality runs.**
3. Promote by `earned_cap`. Demotion is automatic — decay is built into the multiplier.

The evolving agent can raise its cap only by being right. It can never touch the rulebook that enforces the cap — that file is yours.

## What this is not

- Not a trading bot. `teeth` never touches a venue with money; it scores forecasts and meters authority. What you *do* with the authority (paper trading, tool budgets, compute allocation) is your policy layer.
- Not a leaderboard. [ForecastBench](https://www.forecastbench.org/) and the [Metaculus tournaments](https://www.metaculus.com/aib/) measure forecasting skill superbly — and then nothing happens. `teeth` is the *consequence* half: calibration → capital.
- Not financial advice. Obviously.

## Provenance

Born at [Sundai](https://www.sundai.club) (SF), 2026-08-23, extracted from the governance core of **Brise de Mer** — an agent-native paper trading firm whose agents earn their books the same way: by being right about things that hadn't happened yet.

## License

MIT
