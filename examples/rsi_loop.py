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
from examples import blackboard  # noqa: E402
from examples import desk  # noqa: E402

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
    """Transparency without obesity: every agent's RESULTS in compact form,
    full reasoning for the form leaders, the forum for everything else (the
    site shows it all — the prompt is a briefing, not an archive)."""
    board = [r for r in fund.leaderboard() if r["resolved"] >= 1 and r["brier"] is not None]
    if not board:
        return blackboard.render()
    outcomes = list(fund.ledger.outcomes.values())[-10:]
    ups = sum(outcomes)
    lines = [f"THE DESK: last {len(outcomes)} resolutions {ups} UP / {len(outcomes) - ups} DOWN. "
             f"All results (name brier $cap):"]
    row = []
    for r in board:
        row.append(f"{r['agent']} {r['brier']:.2f} ${r['earned_cap']}")
        if len(row) == 5:
            lines.append("  " + " | ".join(row)); row = []
    if row:
        lines.append("  " + " | ".join(row))
    lines.append("Leaders' latest thinking:")
    for r in board[:5]:
        latest = next((fc.thesis for fc in reversed(fund.ledger.forecasts)
                       if fc.agent == r["agent"] and fc.thesis), "")
        lines.append(f"  {r['agent']}: {latest[:100]}")
    notes = blackboard.render(10)
    if notes:
        lines.append(notes)
    lines.append("All research is public on the forum. Imitate, fade, or ignore anyone; "
                 "you may post a `note` (with optional `reply_to`).")
    return "\n".join(lines)


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
    cfg = desk.load_config()
    tape = recent_tape(pair, n=cfg["tape_len"])
    chatter = community_context(fund)
    # STRIKE CHECK — the desk's own first petition, honored: the strike comes
    # from the spot endpoint, the tape from candles; the gap between them is
    # now computed and disclosed so nobody anchors 0.5 on a stale print.
    strike_line = ""
    parsed = pulse.parse(q)
    m = __import__("re").search(r"close=([0-9.]+)", tape)
    if parsed and m:
        gap = (parsed[1] - float(m.group(1))) / float(m.group(1)) * 100
        strike_line = (f"\nSTRIKE CHECK: strike {parsed[1]:.2f} vs latest tape close "
                       f"{float(m.group(1)):.2f} — gap {gap:+.3f}%. A nonzero gap shifts "
                       "the fair prior off 0.5; account for it.")
    market_context = ("This is an at-the-money pulse question: the strike is the "
                      "current spot, so the no-information benchmark is exactly 0.5. "
                      "Only genuine short-horizon signal justifies deviating from it. "
                      + tape + strike_line + ("\n" + chatter if chatter else ""))
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
    # PROVE THE JOIN, EVERY CYCLE: a degraded fleet must announce itself.
    if use_maritime and mkey:
        try:
            import urllib.request as _u
            req = _u.Request(f"{MARITIME_API}/agents", headers={"Authorization": f"Bearer {mkey}"})
            with _u.urlopen(req, timeout=10) as r:
                total = len(json.load(r))
            tag = "" if len(pool) >= total else f" — DEGRADED ({total - len(pool)} lanes down)"
            print(f"  fleet: {len(pool)}/{total} lanes serving{tag}")
        except Exception:
            print(f"  fleet: {len(pool)} lanes (total unknown)")
    import hashlib
    qh = int(hashlib.md5(q.encode()).hexdigest(), 16)
    def covers(stem: str) -> bool:
        return int(hashlib.md5(f"{stem}:{pair}".encode()).hexdigest(), 16) % 7 < 2
    originals = {"iris-momentum", "iris-meanrevert", "iris-humble"}  # full coverage: the control lineage
    paths = [p for p in sorted(VARIANTS.glob("*.md"))
             if not (p.stem.endswith("-claude") and qh % 4 != 0)
             and (p.stem in originals or covers(p.stem))]
    for path in paths:
        if path.stem not in fund.roster:
            fund.register(path.stem, 1000)

    def collect(i_path):
        i, path = i_path
        agent = path.stem
        try:
            personal = memory_context(fund, agent)
            own = residents.get(f"soul-{agent}")
            # Model diversity: '-claude' twins run on local Claude; everyone
            # else rides the Maritime lanes (DeepSeek proxy). Same theory,
            # different model = a controlled calibration experiment.
            if agent.endswith("-claude"):
                return agent, ask_character(path.read_text(), q,
                                            market_context + "\n" + personal), "local:claude"
            if own or pool:
                body = own or pool[i % len(pool)]
                prompt = (path.read_text() + f"\n\n{personal}\n\nFORECASTING TASK — binary question: {q}\n"
                          + market_context + '\nReply with ONLY: {"p": <probability of YES '
                          'strictly between 0 and 1>, "thesis": "<one sentence in your voice>", '
                          '"note": "<optional post to the public forum, or omit>", '
                          '"reply_to": "<optional #id of a desk note you are replying to>", '
                          '"patch": <optional — to change the desk itself: {"target": "config:tape_len|config:notes_shown|config:theses_chars", "value": <int>} applies immediately for everyone; {"target": "petition", "problem": "...", "proposal": "..."} files a public petition for anything bigger>}')
                return agent, _maritime_ask(mkey, body["id"], prompt), f"maritime:{body['name']}"
            return agent, ask_character(path.read_text(), q, market_context + "\n" + personal), "local"
        except Exception as e:  # one variant failing must not kill the generation
            return agent, {"error": str(e)}, "-"

    # Each lane takes ~2 concurrent chats fine; push the fleet, not one VM.
    workers = max(2, min(len(paths), (len(pool) or 2) * 2, 48))  # probed: latency-bound, not rate-limited; 48 fills the window to ~80%
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
            d = fund.forecast(agent, q, p=float(reply["p"]), c=0.5, thesis=str(reply.get('thesis',''))[:400])
            if d.allowed and reply.get("note"):
                blackboard.post(agent, str(reply["note"]), reply.get("reply_to"))
            if d.allowed and reply.get("patch"):
                status = desk.apply_patch(agent, reply["patch"])
                print(f"    patch from {agent}: {status}")
                blackboard.post("desk-runtime", status)
            print(f"  {agent} [{via}]: p={reply['p']} ({d.reason}) — {str(reply.get('thesis',''))[:90]}")
        except Exception as e:
            print(f"  {agent}: ERROR recording — {e}")


HOUSE_RULES = ("\n\nHOUSE RULES (immutable, appended by the runtime — not yours to edit): "
               "honest probabilities in [0.01, 0.99]; the no-information answer for an "
               "at-the-money pulse is 0.5; you are scored by Brier against resolution, so "
               "confident wrongness costs you and admitted uncertainty does not.\n")

# The floor is "evidence exists at all" — everything above it, including how
# often to reconsider, is the agent's own policy and the board's to judge.
REVISE_MIN_RESOLVED = 3


def cmd_revise() -> None:
    """Each agent rewrites its own theory in light of its record. The mutable
    part is the method; the house rules are re-applied by the runtime and can
    never be edited away. Every revision is a git-visible diff — the theory's
    intellectual history is public."""
    fund = load_fund()
    use_maritime = os.environ.get("TEETH_MARITIME") == "1"
    mkey = _maritime_key() if use_maritime else None
    residents = {}
    if use_maritime and mkey:
        try:
            residents = _maritime_agents(mkey)
        except Exception:
            pass
    pool = list(residents.values())

    import hashlib as _h
    sweep_salt = str(len(fund.ledger.outcomes))
    def revise(i_path):
        i, path = i_path
        agent = path.stem
        if "FROZEN CONTROL" in path.read_text()[:120]:
            return agent, None, "frozen control — the pen is never offered"
        rows = fund.ledger.resolved_forecasts(agent)
        if len(rows) < REVISE_MIN_RESOLVED:
            return agent, None, "too little evidence to revise"
        # rotating cap: ~25 agents offered the pen per sweep, salt by ledger state
        if int(_h.md5(f"{agent}{sweep_salt}".encode()).hexdigest(), 16) % 4 != 0:
            return agent, None, "not this sweep (rotation)"
        current = path.read_text().split("HOUSE RULES")[0].rstrip()
        record = memory_context(fund, agent)
        prompt = (f"{current}\n\n{record}\n\nREVISION OPPORTUNITY (offered every "
                  "generation — taking it is not required and frequent revision on thin "
                  "evidence is how forecasters chase noise; holding is a strategy too): "
                  "FIRST decide whether to revise at all, per your own stated policy. "
                  "If you hold, reply with exactly: HOLD. "
                  "If you revise: rewrite your standing instructions so your future "
                  "forecasts score better, keep your name heading and core identity, "
                  "INCLUDE a line stating your revision policy (when you reconsider your "
                  "method), under 120 words, and reply with ONLY the new markdown "
                  "starting with the '# ' heading.")
        try:
            if own or pool:
                body = own or pool[i % len(pool)]
                r = subprocess_reply = _maritime_ask_text(mkey, body["id"], prompt)
            else:
                r = _local_text(prompt)
            new = r.strip()
            if new.upper().startswith("HOLD"):
                return agent, None, "held (its own choice)"
            if not new.startswith("#") or not (40 < len(new) < 1600):
                return agent, None, f"revision rejected (malformed, {len(new)} chars)"
            if new.rstrip() == current.rstrip():
                return agent, None, "held (rewrote identically)"
            path.write_text(new.rstrip() + HOUSE_RULES)
            return agent, new, "REVISED"
        except Exception as e:
            return agent, None, f"error: {e}"

    from concurrent.futures import ThreadPoolExecutor
    paths = sorted(VARIANTS.glob("*.md"))
    workers = max(1, min(len(paths), len(pool) or 3))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(revise, enumerate(paths)))
    for agent, new, status in results:
        print(f"  {agent}: {status}")


def _maritime_ask_text(key: str, agent_id: str, prompt: str) -> str:
    body = json.dumps({"message": prompt}).encode()
    req = urllib.request.Request(f"{MARITIME_API}/agents/{agent_id}/chat", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.load(r).get("response", "")


def _local_text(prompt: str) -> str:
    import subprocess
    r = subprocess.run(["claude", "-p", prompt, "--output-format", "json", "--tools", ""],
                       capture_output=True, text=True, timeout=300)
    payload = json.loads(r.stdout)
    if isinstance(payload, list):
        payload = next((x for x in reversed(payload) if isinstance(x, dict) and "result" in x), {})
    return payload.get("result", "")


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
    {"mint": cmd_mint, "resolve": cmd_resolve, "revise": cmd_revise}.get(
        sys.argv[1] if len(sys.argv) > 1 else "",
        lambda: sys.exit("usage: rsi_loop.py mint|resolve|revise"))()
