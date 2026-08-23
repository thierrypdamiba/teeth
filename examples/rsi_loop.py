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
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teeth import Fund, pulse  # noqa: E402
from examples.character_agent import ask_character  # noqa: E402

MARITIME_API = "https://api.maritime.sh/api"


def _maritime_key() -> str | None:
    try:
        return json.load(open(os.path.expanduser("~/.config/maritime/credentials.json")))["api_key"]
    except Exception:
        return None


def _maritime_agents(key: str) -> dict:
    req = urllib.request.Request(f"{MARITIME_API}/agents",
                                 headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        # Sleeping residents wake on request (that's Maritime's whole
        # architecture) — only error/deploying states are unusable.
        return {a["name"]: a for a in json.load(r)
                if a.get("status") in ("active", "sleeping")}


def _maritime_ask(key: str, agent_id: str, prompt: str) -> dict:
    body = json.dumps({"message": prompt}).encode()
    req = urllib.request.Request(f"{MARITIME_API}/agents/{agent_id}/chat", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        text = json.load(r).get("response", "")
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def recent_tape(pair: str = "BTC-USD", n: int = 12) -> str:
    """Last n 5-minute closes from Coinbase's public candles — the same tape
    for every variant, injected into the prompt so hosted agents (no tools)
    and local agents (tools) forecast from identical information."""
    try:
        req = urllib.request.Request(
            f"https://api.exchange.coinbase.com/products/{pair}/candles?granularity=300",
            headers={"User-Agent": "teeth/0.1"})
        with urllib.request.urlopen(req, timeout=10) as r:
            candles = json.load(r)[:n]  # newest first: [time, low, high, open, close, vol]
        lines = [f"t-{i * 5}min close={c[4]:.2f}" for i, c in enumerate(candles)]
        return "Recent 5-min closes (newest first): " + "; ".join(lines)
    except Exception:
        return "No tape available — treat as a quiet, unknown market."

LEDGER = str(ROOT / "ledger.jsonl")
ROSTER = str(ROOT / "roster.json")
VARIANTS = ROOT / "variants"
# 5-minute generations: the floor is agent inference time (~60-90s per
# headless run) plus feed latency — below that an agent finishes "forecasting"
# after the answer already exists. 5 min clears the floor with margin and
# yields 12 generations/hour of real selection pressure.
HORIZON_S = 300


def load_fund() -> Fund:
    fund = Fund(LEDGER, min_edge=0.0)
    for agent, cap in json.load(open(ROSTER)).items():
        fund.register(agent, cap)
    return fund


def memory_context(fund: Fund, agent: str) -> str:
    """The agent's own record, shown to it: the raw material of self-improvement.
    Mechanical (no extra LLM calls) — the agent sees what happened and is told
    to update. In-context learning IS the inner improvement loop."""
    rows = fund.ledger.resolved_forecasts(agent)
    if not rows:
        return "YOUR RECORD: no resolved forecasts yet."
    recent = rows[-6:]
    lines = [f"  p={fc.p:.2f} -> {'YES' if out else 'NO'} (brier {(fc.p - (1.0 if out else 0.0))**2:.3f})"
             for fc, out in recent]
    b = sum((fc.p - (1.0 if out else 0.0)) ** 2 for fc, out in rows) / len(rows)
    return (f"YOUR RECORD ({len(rows)} resolved, mean brier {b:.3f} — "
            f"{'beating' if b < 0.25 else 'losing to' if b > 0.25 else 'matching'} the 0.5 benchmark):\n"
            + "\n".join(lines)
            + "\nUpdate your approach based on this record: if your method has been "
            "losing, trust it less this round; if winning, hold course. Say what you changed.")


def community_context(fund: Fund) -> str:
    """The desk chatter: what the whole community's record shows, shared with
    everyone. Collective memory without shared identity."""
    board = [r for r in fund.leaderboard() if r["resolved"] >= 4 and r["brier"] is not None]
    if len(board) < 3:
        return ""
    top, bottom = board[0], board[-1]
    outcomes = list(fund.ledger.outcomes.values())[-8:]
    ups = sum(outcomes)
    return (f"DESK CHATTER (shared with all agents): best performer is {top['agent']} "
            f"(brier {top['brier']:.3f}), worst is {bottom['agent']} ({bottom['brier']:.3f}). "
            f"Last {len(outcomes)} resolutions: {ups} UP / {len(outcomes) - ups} DOWN. "
            "Weigh the crowd's record as evidence, not authority.")


def cmd_mint() -> None:
    fund = load_fund()
    pair = os.environ.get("TEETH_PAIR", "BTC-USD")
    if "-" not in pair and not pulse.equity_market_open():
        print(f"{pair}: market closed — no pulse minted")
        return
    q = pulse.mint(pair, HORIZON_S)
    if q is None:
        sys.exit("no spot print — refusing to mint")
    print(f"minted {q}")
    tape = recent_tape()
    chatter = community_context(fund)
    market_context = ("This is an at-the-money pulse question: the strike is the "
                      "current spot, so the no-information benchmark is exactly 0.5. "
                      "Only genuine short-horizon signal justifies deviating from it. "
                      + tape + ("\n" + chatter if chatter else ""))
    use_maritime = os.environ.get("TEETH_MARITIME") == "1"
    mkey = _maritime_key() if use_maritime else None
    residents = {}
    if use_maritime and mkey:
        try:
            residents = _maritime_agents(mkey)
        except Exception as e:
            print(f"  maritime unreachable ({e}) — falling back to local sessions")
    # Round-robin over resident VMs, in parallel: a character is a prompt, a
    # resident is a body — N bodies host any number of souls concurrently, and
    # Maritime's flat pricing explicitly doesn't meter messages. A population
    # of 20 collects inside a minute of wall-clock.
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timezone
    pool = list(residents.values())
    paths = sorted(VARIANTS.glob("*.md"))
    for path in paths:
        if path.stem not in fund.roster:
            fund.register(path.stem, 1000)

    def collect(i_path):
        i, path = i_path
        agent = path.stem
        try:
            personal = memory_context(fund, agent)
            if pool:
                body = pool[i % len(pool)]
                prompt = (path.read_text() + f"\n\n{personal}\n\nFORECASTING TASK — binary question: {q}\n"
                          + market_context + '\nReply with ONLY: {"p": <probability of YES '
                          'strictly between 0 and 1>, "thesis": "<one sentence in your voice>"}')
                return agent, _maritime_ask(mkey, body["id"], prompt), f"maritime:{body['name']}"
            return agent, ask_character(path.read_text(), q, market_context + "\n" + personal), "local"
        except Exception as e:  # one variant failing must not kill the generation
            return agent, {"error": str(e)}, "-"

    workers = max(1, min(len(paths), len(pool) or 3))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(collect, enumerate(paths)))

    _, _, deadline = pulse.parse(q)
    for agent, reply, via in results:
        if "error" in reply:
            print(f"  {agent}: ERROR {reply['error'][:120]}")
            continue
        # Look-ahead guard: a forecast that arrives after the deadline is
        # not a forecast — the answer already exists. Refuse, don't record.
        if datetime.now(timezone.utc) >= deadline:
            print(f"  {agent}: TOO SLOW — inference outlasted the horizon, refused")
            continue
        try:
            d = fund.forecast(agent, q, p=float(reply["p"]), c=0.5)
            print(f"  {agent} [{via}]: p={reply['p']} ({d.reason}) — {str(reply.get('thesis',''))[:90]}")
        except Exception as e:
            print(f"  {agent}: ERROR recording — {e}")


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
