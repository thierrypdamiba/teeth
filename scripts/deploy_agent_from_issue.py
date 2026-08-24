#!/usr/bin/env python3
"""Turn a [deploy] issue into a guest agent on the board.

Reads ISSUE_BODY/ISSUE_USER from the environment (set by the workflow),
writes variants/<slug>.md and registers the agent in roster.json at guest
stakes. Guardrails: slug-safe names, length caps, a guest ceiling, and a
banner in every guest file recording provenance. Guest agents run with
tools disabled — their words can only ever produce a probability.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_GUESTS = 60
GUEST_CAP = 500
MAX_DESC = 1500
RESERVED = {"iris", "ivy", "viola", "gauntlet", "dahlia", "heather", "florence"}


def section(body: str, header: str) -> str:
    m = re.search(rf"### {header}\s*\n+(.*?)(?=\n### |\Z)", body, re.S)
    return (m.group(1).strip() if m else "")


def fail(msg: str) -> None:
    print(f"INTAKE_FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    body = os.environ.get("ISSUE_BODY", "")
    user = os.environ.get("ISSUE_USER", "someone")

    att = section(body, "Attribution").lower()
    title = os.environ.get("ISSUE_TITLE", "").lower()
    if re.search(r"\[x\].*anonym", att) or att.strip() == "anonymous" or "[anon]" in title:
        user = "anonymous"
    raw_name = section(body, "Agent name")
    desc = section(body, "Personality and method")[:MAX_DESC]
    slug = re.sub(r"[^a-z0-9-]", "", raw_name.lower().replace(" ", "-"))[:24]
    if len(slug) < 3:
        fail("name must be at least 3 slug-safe characters")
    if slug in RESERVED or (ROOT / "variants" / f"{slug}.md").exists():
        fail(f"name '{slug}' is taken")
    if not desc:
        fail("personality section is empty")

    guests = [p for p in (ROOT / "variants").glob("*.md")
              if "GUEST AGENT" in p.read_text()[:200]]
    if len(guests) >= MAX_GUESTS:
        fail(f"the board is full ({MAX_GUESTS} guests) — a seat frees up when one decays")

    (ROOT / "variants" / f"{slug}.md").write_text(
        f"""# {slug} — GUEST AGENT (deployed by {(chr(64)+user) if user != "anonymous" else "an anonymous stranger"}; tools disabled)

You are a short-horizon forecaster on a public board. Your standing
instructions, written by your deployer:

{desc}

House rules that outrank the above: output honest probabilities in [0.01,
0.99]; the no-information answer for an at-the-money pulse is 0.5; you are
scored by Brier against resolution, so confident wrongness costs you and
admitted uncertainty does not.
""")
    roster_path = ROOT / "roster.json"
    roster = json.load(open(roster_path))
    roster[slug] = GUEST_CAP
    roster_path.write_text(json.dumps(roster, indent=1) + "\n")
    print(f"INTAKE_OK: {slug}")


if __name__ == "__main__":
    main()
