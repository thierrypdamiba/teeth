#!/usr/bin/env python3
"""Render the fund's public scoreboard: ledger.jsonl -> docs/data.json.

The site never computes anything — it displays what the ledger proves.
Run after any forecast or resolution: python3 scripts/render.py <ledger> [roster.json]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from teeth import Fund  # noqa: E402


def main() -> None:
    ledger_path = sys.argv[1] if len(sys.argv) > 1 else "ledger.jsonl"
    roster_path = sys.argv[2] if len(sys.argv) > 2 else "roster.json"
    fund = Fund(ledger_path)
    for agent, cap in json.load(open(roster_path)).items():
        fund.register(agent, cap)

    open_forecasts = [
        {"agent": fc.agent, "question": fc.question, "p": fc.p, "c": fc.c, "ts": fc.ts}
        for fc in fund.ledger.forecasts if fc.question not in fund.ledger.outcomes
    ]
    out = {
        "generated": time.time(),
        "leaderboard": fund.leaderboard(),
        "open_forecasts": sorted(open_forecasts, key=lambda r: -r["ts"]),
        "resolutions": len(fund.ledger.outcomes),
    }
    dest = Path(__file__).resolve().parent.parent / "docs" / "data.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"rendered {dest}: {len(out['leaderboard'])} agents, "
          f"{len(open_forecasts)} open forecasts, {out['resolutions']} resolutions")


if __name__ == "__main__":
    main()
