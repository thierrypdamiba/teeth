#!/usr/bin/env python3
"""The slow track: real open-world questions, the kind external benchmarks ask.

Pulls liquid open binary markets from Manifold (closing 2-30 days out), has the
flagship character forecast each with research enabled, and records them with
the market's price as the benchmark. This is the track that trains for
ForecastBench/Metaculus — world events, not microstructure.

    python3 scripts/slow_slate.py [--n 5] [--character ../brise-de-mer/characters/iris.md] [--agent iris]
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

MANIFOLD_CREDS = Path.home() / ".config/manifold/credentials.json"


def place_bet(market_id: str, p: float, c: float) -> str:
    """Kelly-sized mana bet under the forecast — the third-party public record.
    Skips thin edges; sized off a 100-mana reference cap, floored/capped 5-40."""
    try:
        api_key = json.load(open(MANIFOLD_CREDS))["api_key"]
    except Exception:
        return "no manifold creds"
    edge = p - c
    if abs(edge) < 0.03:
        return "edge too thin to bet"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from teeth.allocate import kelly_stake
    side = "buy" if edge > 0 else "sell"
    amount = max(5, min(40, kelly_stake(100, p, c, side)))
    outcome = "YES" if edge > 0 else "NO"
    body = json.dumps({"amount": amount, "contractId": market_id, "outcome": outcome}).encode()
    req = urllib.request.Request("https://api.manifold.markets/v0/bet", data=body,
                                 headers={"Authorization": f"Key {api_key}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            json.load(r)
        return f"BET M{amount} {outcome}"
    except Exception as e:
        return f"bet failed: {str(e)[:60]}"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teeth import Fund  # noqa: E402
from examples.character_agent import ask_character  # noqa: E402


def open_slate(n: int) -> list[dict]:
    req = urllib.request.Request("https://api.manifold.markets/v0/markets?limit=250",
                                 headers={"User-Agent": "teeth/0.1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        markets = json.load(r)
    now = time.time() * 1000
    picks = []
    for m in markets:
        if m.get("outcomeType") != "BINARY" or m.get("isResolved"):
            continue
        days = ((m.get("closeTime") or 0) - now) / 86400000
        p = m.get("probability") or 0
        if 2 <= days <= 30 and 0.05 < p < 0.95 and (m.get("uniqueBettorCount") or 0) >= 15:
            picks.append({"id": m["id"], "slug": m["slug"], "question": m["question"],
                          "prob": p, "days": round(days, 1)})
        if len(picks) >= n:
            break
    return picks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--character", default=str(Path.home() / "brise-de-mer/characters/iris.md"))
    ap.add_argument("--agent", default="iris")
    ap.add_argument("--ledger", default=str(ROOT / "ledger.jsonl"))
    ap.add_argument("--roster", default=str(ROOT / "roster.json"))
    ap.add_argument("--bet", action="store_true",
                    help="place real mana bets under each recorded forecast")
    args = ap.parse_args()

    fund = Fund(args.ledger)
    for a, cap in json.load(open(args.roster)).items():
        fund.register(a, cap)
    character_md = Path(args.character).read_text()
    already = {fc.question for fc in fund.ledger.forecasts if fc.agent == args.agent}

    for mkt in open_slate(args.n):
        qid = f"manifold:{mkt['slug']}"
        if qid in already:
            continue
        try:
            reply = ask_character(
                character_md, f"{mkt['question']} (closes in ~{mkt['days']} days)",
                f"The market currently prices YES at {mkt['prob']:.3f}. You may research "
                "(you have tools). Name your reference class or your source in the thesis.")
            d = fund.forecast(args.agent, qid, p=float(reply["p"]), c=mkt["prob"], thesis=str(reply.get("thesis",""))[:400])
            bet = place_bet(mkt["id"], float(reply["p"]), mkt["prob"]) if (args.bet and d.allowed) else "not betting"
            print(json.dumps({"q": mkt["question"][:80], "p": reply.get("p"),
                              "c": round(mkt["prob"], 3), "decision": d.reason,
                              "bet": bet,
                              "thesis": str(reply.get("thesis", ""))[:110]}))
        except Exception as e:
            print(f"SKIP {qid}: {e}")


if __name__ == "__main__":
    main()
