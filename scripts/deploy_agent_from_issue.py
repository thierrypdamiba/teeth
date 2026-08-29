#!/usr/bin/env python3
"""Turn a [deploy] issue into a guest agent on the board.

Reads ISSUE_BODY/ISSUE_USER from the environment (set by the workflow),
writes variants/<slug>.md and registers the agent in roster.json at guest
stakes. Guardrails: slug-safe names, length caps, a guest ceiling, and a
banner in every guest file recording provenance. Guest agents run with
tools disabled — their words can only ever produce a probability.
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teeth.competition import load_config, parse_utc, strategy_digest, validate_registry  # noqa: E402

GUEST_CAP = 500
MAX_DESC = 1200
RESERVED = {"iris", "ivy", "viola", "gauntlet", "dahlia", "heather", "florence"}
RULES_MARKER = "<!-- TEETH_RUNTIME_RULES_V1 -->"


def section(body: str, header: str) -> str:
    m = re.search(rf"### {header}\s*\n+(.*?)(?=\n### |\Z)", body, re.S)
    return (m.group(1).strip() if m else "")


def fail(msg: str) -> None:
    print(f"INTAKE_FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    body = os.environ.get("ISSUE_BODY", "")
    user = os.environ.get("ISSUE_USER", "")
    user_id = os.environ.get("ISSUE_USER_ID", "")
    issue_number = os.environ.get("ISSUE_NUMBER", "")
    submitted_at = os.environ.get("ISSUE_CREATED_AT", "")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", user):
        fail("missing or invalid GitHub owner")
    if not user_id.isdigit() or not issue_number.isdigit() or int(issue_number) <= 0:
        fail("missing stable GitHub identity or source issue")
    try:
        submitted = parse_utc(submitted_at)
    except ValueError:
        fail("missing trusted issue creation time")

    season = load_config(ROOT)
    registration_close = parse_utc(season["registration_closes_at"])
    if submitted >= registration_close or datetime.now(timezone.utc) >= registration_close:
        fail(f"registration for {season['id']} is closed")
    registry_path = ROOT / "entrants.json"
    registry = json.loads(registry_path.read_text())
    if registry.get("season_id") != season["id"]:
        fail("entrant registry is not configured for the current season")
    identity = hashlib.sha256(f"github:{user_id}".encode()).hexdigest()
    if any(row.get("identity_sha256") == identity
           for row in registry.get("entrants", {}).values()):
        fail("this GitHub identity already entered an agent this season")

    att = section(body, "Attribution").lower()
    title = os.environ.get("ISSUE_TITLE", "").lower()
    if re.search(r"\[x\].*anonym", att) or att.strip() == "anonymous" or "[anon]" in title:
        user = "anonymous"
    raw_name = section(body, "Agent name")
    desc = section(body, "Personality and method")[:MAX_DESC]
    desc = "".join(ch for ch in desc if ch in "\n\t" or ord(ch) >= 32).strip()
    slug = re.sub(r"[^a-z0-9-]", "", raw_name.lower().replace(" ", "-"))[:24].strip("-")
    if len(slug) < 3:
        fail("name must be at least 3 slug-safe characters")
    if slug in RESERVED or (ROOT / "variants" / f"{slug}.md").exists():
        fail(f"name '{slug}' is taken")
    if not desc:
        fail("personality section is empty")

    if len(registry["entrants"]) >= int(season["maximum_entrants"]):
        fail(f"the season is full ({season['maximum_entrants']} entrants)")

    original = f"# {slug}\n\n{desc}\n"
    submission_dir = ROOT / "submissions" / season["id"]
    submission_dir.mkdir(parents=True, exist_ok=True)
    (submission_dir / f"{slug}.md").write_text(original)

    (ROOT / "variants" / f"{slug}.md").write_text(
        f"""# {slug}

You are a short-horizon forecaster on a public board. Your standing
instructions, written by your deployer:

{desc}

{RULES_MARKER}
House rules that outrank the above: output honest probabilities in [0.01,
0.99]; the no-information answer for an at-the-money pulse is 0.5; you are
scored by Brier against resolution, so confident wrongness costs you and
admitted uncertainty does not.
""")
    roster_path = ROOT / "roster.json"
    roster = json.load(open(roster_path))
    roster[slug] = GUEST_CAP
    roster_path.write_text(json.dumps(roster, indent=1) + "\n")
    registry["entrants"][slug] = {
        "identity_sha256": identity,
        "public_by": None if user == "anonymous" else f"@{user}",
        "issue_number": int(issue_number),
        "submitted_at": submitted.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategy_sha256": strategy_digest(original),
        "eligible": True,
        "manual_edits": "frozen_at_submission"
    }
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")
    validate_registry(ROOT)
    print(f"INTAKE_OK: {slug}")


if __name__ == "__main__":
    main()
