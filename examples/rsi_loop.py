#!/usr/bin/env python3
"""The selection loop, at pulse speed: variants forecast, reality resolves,
authority moves. One generation per invocation — run it on a timer and the
leaderboard becomes natural selection you can watch.

    python3 examples/rsi_loop.py mint      # mint a pulse question + collect forecasts
    python3 examples/rsi_loop.py resolve   # resolve due questions + re-render the board

Variants are character files in a directory (default variants/): each is a
different harness for the same job. Their earned caps ARE the fitness scores.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teeth import Fund, pulse  # noqa: E402
from examples.character_agent import ask_character  # noqa: E402

LEDGER = str(ROOT / "ledger.jsonl")
ROSTER = str(ROOT / "roster.json")
VARIANTS = ROOT / "variants"
HORIZON_S = 1800  # 30-minute generations


def load_fund() -> Fund:
    fund = Fund(LEDGER, min_edge=0.0)
    for agent, cap in json.load(open(ROSTER)).items():
        fund.register(agent, cap)
    return fund


def cmd_mint() -> None:
    fund = load_fund()
    q = pulse.mint("BTC-USD", HORIZON_S)
    if q is None:
        sys.exit("no spot print — refusing to mint")
    print(f"minted {q}")
    for path in sorted(VARIANTS.glob("*.md")):
        agent = path.stem
        if agent not in fund.roster:
            fund.register(agent, 1000)
        try:
            reply = ask_character(
                path.read_text(), q,
                "This is an at-the-money pulse question: the strike is the "
                "current spot, so the no-information benchmark is exactly 0.5. "
                "Only genuine short-horizon signal justifies deviating from it.")
            d = fund.forecast(agent, q, p=float(reply["p"]), c=0.5)
            print(f"  {agent}: p={reply['p']} ({d.reason}) — {reply.get('thesis','')[:90]}")
        except Exception as e:  # one variant failing must not kill the generation
            print(f"  {agent}: ERROR {e}")


def cmd_resolve() -> None:
    fund = load_fund()
    for q, outcome in pulse.resolve_due(fund.ledger):
        print(f"resolved {q} -> {'YES' if outcome else 'NO'}")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "render.py"), LEDGER, ROSTER],
                   check=False)
    for row in fund.leaderboard():
        print(f"  {row['agent']:<14} resolved={row['resolved']:<3} "
              f"brier={row['brier'] if row['brier'] is None else round(row['brier'],3)} "
              f"cap=${row['earned_cap']}/{row['standing_cap']}")


if __name__ == "__main__":
    {"mint": cmd_mint, "resolve": cmd_resolve}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: rsi_loop.py mint|resolve"))()
