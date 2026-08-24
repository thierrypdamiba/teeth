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
from examples import blackboard, desk  # noqa: E402


def main() -> None:
    ledger_path = sys.argv[1] if len(sys.argv) > 1 else "ledger.jsonl"
    roster_path = sys.argv[2] if len(sys.argv) > 2 else "roster.json"
    fund = Fund(ledger_path)
    for agent, cap in json.load(open(roster_path)).items():
        fund.register(agent, cap)

    open_forecasts = [
        {"agent": fc.agent, "question": fc.question, "p": fc.p, "c": fc.c, "ts": fc.ts, "thesis": fc.thesis}
        for fc in fund.ledger.forecasts if fc.question not in fund.ledger.outcomes
    ]
    # Desk-grade analytics: recent form, trajectories, dispersion.
    from collections import defaultdict
    seq = defaultdict(list)  # agent -> [brier per resolved forecast, in order]
    for fc in fund.ledger.forecasts:
        if fc.question in fund.ledger.outcomes:
            o = 1.0 if fund.ledger.outcomes[fc.question] else 0.0
            seq[fc.agent].append(round((fc.p - o) ** 2, 4))
    analytics = {}
    for a, xs in seq.items():
        roll = xs[-12:]
        analytics[a] = {"rolling12": round(sum(roll) / len(roll), 3) if roll else None,
                        "spark": xs[-30:]}
    # Dispersion on open questions: the desk's disagreement is a signal.
    by_q = defaultdict(list)
    for fc in fund.ledger.forecasts:
        if fc.question not in fund.ledger.outcomes:
            by_q[fc.question].append(fc.p)
    dispersion = []
    for qq, ps in by_q.items():
        if len(ps) >= 3:
            mean = sum(ps) / len(ps)
            sd = (sum((x - mean) ** 2 for x in ps) / len(ps)) ** 0.5
            dispersion.append({"question": qq, "n": len(ps), "mean": round(mean, 3),
                               "sd": round(sd, 3), "min": round(min(ps), 2), "max": round(max(ps), 2)})
    dispersion.sort(key=lambda r: -r["sd"])
    tape = [{"q": q.split("@")[0].replace("pulse:", ""), "outcome": o}
            for q, o in list(fund.ledger.outcomes.items())[-12:]]
    # SEASON scoring: sum of edge-vs-benchmark this calendar month. Cowardice
    # scores zero, volume compounds edge, luck dilutes at n. The purse metric.
    import datetime as _dt
    month_start = _dt.datetime.now(_dt.timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
    season = defaultdict(lambda: {"edge_sum": 0.0, "n": 0})
    for fc in fund.ledger.forecasts:
        if fc.ts >= month_start and fc.question in fund.ledger.outcomes:
            o = 1.0 if fund.ledger.outcomes[fc.question] else 0.0
            season[fc.agent]["edge_sum"] += (fc.c - o) ** 2 - (fc.p - o) ** 2
            season[fc.agent]["n"] += 1
    QUALIFY_N = 200
    season_rows = sorted(
        ({"agent": a, "edge_sum": round(v["edge_sum"], 3), "n": v["n"],
          "qualified": v["n"] >= QUALIFY_N} for a, v in season.items()),
        key=lambda r: -r["edge_sum"])
    resolved_theses = []
    for fc in fund.ledger.forecasts[-160:]:
        if fc.question in fund.ledger.outcomes and fc.thesis:
            out_come = fund.ledger.outcomes[fc.question]
            resolved_theses.append({
                "agent": fc.agent, "p": fc.p, "outcome": out_come,
                "brier": round((fc.p - (1.0 if out_come else 0.0)) ** 2, 3),
                "thesis": fc.thesis, "ts": fc.ts})
    out = {
        "generated": time.time(),
        "leaderboard": fund.leaderboard(),
        "open_forecasts": sorted(open_forecasts, key=lambda r: -r["ts"]),
        "resolutions": len(fund.ledger.outcomes),
        "desk_notes": blackboard.read(20),
        "board": blackboard.archive(500),
        "profiles": {
            p.stem: {
                "bio": p.read_text().split("HOUSE RULES")[0].split("\n", 1)[-1].strip()[:400],
            } for p in (Path(ledger_path).parent / "variants").glob("*.md")
        },
        "recent_theses": resolved_theses[-40:],
        "desk_config": desk.load_config(),
        "analytics": analytics,
        "dispersion": dispersion[:6],
        "tape": tape,
        "season": {"rows": season_rows[:15], "qualify_n": QUALIFY_N,
                   "purse": "$1,000", "ends": "end of month"},
        "machine": {
            "souls": len(list((Path(ledger_path).parent / "variants").glob("*.md"))),
            "forecasts_total": len(fund.ledger.forecasts),
            "resolutions_total": len(fund.ledger.outcomes),
            "markets": 7,
            "generation_seconds": 300,
            "theses_chars": sum(len(fc.thesis) for fc in fund.ledger.forecasts),
        },
    }
    dest = Path(__file__).resolve().parent.parent / "docs" / "data.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"rendered {dest}: {len(out['leaderboard'])} agents, "
          f"{len(open_forecasts)} open forecasts, {out['resolutions']} resolutions")


if __name__ == "__main__":
    main()
