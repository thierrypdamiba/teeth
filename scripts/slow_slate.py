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
            picks.append({"slug": m["slug"], "question": m["question"],
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
            print(json.dumps({"q": mkt["question"][:80], "p": reply.get("p"),
                              "c": round(mkt["prob"], 3), "decision": d.reason,
                              "thesis": str(reply.get("thesis", ""))[:110]}))
        except Exception as e:
            print(f"SKIP {qid}: {e}")


if __name__ == "__main__":
    main()
