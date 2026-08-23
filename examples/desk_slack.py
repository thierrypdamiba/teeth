#!/usr/bin/env python3
"""The desk gets Slack: a per-cycle digest to the firm's #social channel.

Over-communication doctrine: the agents' work should be legible where the
humans live. Token is read from the firm vault at runtime, never stored here.
Silent no-op if the vault or channel is unreachable — Slack is a window,
never a dependency.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teeth import Fund  # noqa: E402
from examples import blackboard  # noqa: E402

CHANNEL = "C0BHCNHDP5Y"  # #social
VAULT = Path.home() / "brise-de-mer" / ".env"


def token() -> str | None:
    try:
        m = re.search(r"^SLACK_BOT_TOKEN=(.+)$", VAULT.read_text(), re.M)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def main() -> None:
    tok = token()
    if not tok:
        return
    fund = Fund(str(ROOT / "ledger.jsonl"))
    for a, c in json.load(open(ROOT / "roster.json")).items():
        fund.register(a, c)
    board = [r for r in fund.leaderboard() if r["resolved"] and r["brier"] is not None]
    if not board:
        return
    top3 = board[:3]
    outcomes = list(fund.ledger.outcomes.items())[-3:]
    notes = blackboard.read(3)

    lines = ["🦷 *the desk* — generation digest"]
    lines += [f"• {q.split('@')[0].replace('pulse:', '')} → *{'YES' if o else 'NO'}*"
              for q, o in outcomes]
    lines.append("*Leaders:* " + " · ".join(
        f"{r['agent']} ({r['brier']:.3f}, ${r['earned_cap']})" for r in top3))
    for n in notes:
        lines.append(f"> [{n['agent']}] {n['note'][:150]}")
    lines.append(f"<https://thierrypdamiba.github.io/teeth/|the board>")

    body = json.dumps({"channel": CHANNEL, "text": "\n".join(lines)}).encode()
    req = urllib.request.Request("https://slack.com/api/chat.postMessage", data=body,
                                 headers={"Authorization": f"Bearer {tok}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.load(r)
        print("slack:", "ok" if resp.get("ok") else resp.get("error"))
    except Exception as e:
        print(f"slack unreachable ({e}) — carrying on")


if __name__ == "__main__":
    main()
