#!/usr/bin/env python3
"""The desk, live in Slack — and it jumps.

Every generation: agents' fresh blackboard notes post AS the agents (name +
emoji), and one digest tracks what a floor actually watches — capital moves,
lead changes, the tape. State file dedupes so nothing posts twice. Token from
the firm vault at runtime; silent no-op without it.
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
STATE = ROOT / ".slack_state.json"
EMOJI = [":ocean:", ":fire:", ":crystal_ball:", ":chart_with_upwards_trend:",
         ":game_die:", ":brain:", ":zap:", ":mag:", ":scales:", ":dart:",
         ":tophat:", ":robot_face:", ":mountain:", ":wave:", ":dizzy:"]


def token() -> str | None:
    try:
        m = re.search(r"^SLACK_BOT_TOKEN=(.+)$", VAULT.read_text(), re.M)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def post(tok: str, text: str, username: str | None = None, icon: str | None = None) -> None:
    body = {"channel": CHANNEL, "text": text}
    if username:
        body["username"] = username
        body["icon_emoji"] = icon or ":robot_face:"
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def emoji_for(agent: str) -> str:
    return EMOJI[sum(ord(c) for c in agent) % len(EMOJI)]


def main() -> None:
    tok = token()
    if not tok:
        return
    fund = Fund(str(ROOT / "ledger.jsonl"))
    for a, c in json.load(open(ROOT / "roster.json")).items():
        fund.register(a, c)

    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except Exception:
            state = {}
    prev_caps = state.get("caps", {})
    last_note_ts = state.get("last_note_ts", 0)
    prev_leader = state.get("leader")
    prev_res = state.get("resolutions", 0)

    board = [r for r in fund.leaderboard() if r["resolved"] and r["brier"] is not None]
    if not board:
        return

    # 1. Agents speak as themselves: fresh notes only, capped per cycle.
    fresh = [n for n in blackboard.read(30) if n.get("ts", 0) > last_note_ts][-4:]
    for n in fresh:
        post(tok, n["note"], username=n["agent"], icon=emoji_for(n["agent"]))
        last_note_ts = max(last_note_ts, n.get("ts", 0))

    # 2. The digest: what a floor watches.
    lines = []
    new_res = list(fund.ledger.outcomes.items())[prev_res:][-6:]
    if new_res:
        lines.append(" · ".join(
            f"{q.split('@')[0].replace('pulse:', '')} {'▲YES' if o else '▼NO'}"
            for q, o in new_res))
    movers = []
    for r in board:
        prev = prev_caps.get(r["agent"])
        if prev is not None and r["earned_cap"] != prev:
            d = r["earned_cap"] - prev
            movers.append((abs(d), f"{r['agent']} {'+' if d > 0 else ''}{d} → ${r['earned_cap']}"))
    if movers:
        movers.sort(reverse=True)
        lines.append("💰 " + " · ".join(m[1] for m in movers[:4]))
    leader = board[0]["agent"]
    if prev_leader and leader != prev_leader:
        lines.append(f"👑 *LEAD CHANGE: {leader} takes the desk* (from {prev_leader})")
    lines.append(f"top: " + " · ".join(
        f"{r['agent']} ({r['brier']:.3f}, ${r['earned_cap']})" for r in board[:3])
        + f" · <https://thierrypdamiba.github.io/teeth/|board>")
    if len(lines) > 1 or new_res:
        post(tok, "🦷 " + "\n".join(lines))

    STATE.write_text(json.dumps({
        "caps": {r["agent"]: r["earned_cap"] for r in board},
        "last_note_ts": last_note_ts,
        "leader": leader,
        "resolutions": len(fund.ledger.outcomes),
    }))
    print("slack: jumped")


if __name__ == "__main__":
    main()
