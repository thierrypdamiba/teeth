"""The desk's self-patching surface — bounded freedom, orita-style.

Agents can change their shared environment two ways:

1. CONFIG PATCHES — applied immediately, no human in the loop, because the
   surface is typed and bounded: a whitelisted set of numeric knobs on the
   context the desk sees. An agent can widen the tape or the note window for
   everyone; it cannot inject a single character of free text into anyone's
   prompt. Freedom over parameters, never over words.

2. PETITIONS — free-text proposals for anything else (scoring, mechanics,
   new capabilities). Filed to petitions/ on the public record, announced on
   the blackboard, decided by the operator. The constitution (ledger,
   scoring, house rules) is not editable from inside, by design: the whole
   experiment is evolution inside an invariant envelope.
"""

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "desk_config.json"
PETITIONS = ROOT / "petitions"

# knob: (min, max, default) — the entire mutable surface, typed and bounded.
KNOBS = {
    "tape_len": (4, 24, 12),
    "notes_shown": (5, 30, 15),
    "theses_chars": (60, 240, 110),
}


def load_config() -> dict:
    cfg = {k: v[2] for k, v in KNOBS.items()}
    if CONFIG.exists():
        try:
            saved = json.load(open(CONFIG))
            for k, (lo, hi, _) in KNOBS.items():
                if isinstance(saved.get(k), int) and lo <= saved[k] <= hi:
                    cfg[k] = saved[k]
        except Exception:
            pass
    return cfg


def apply_patch(agent: str, patch: dict) -> str:
    """Returns a status string; config changes apply now, petitions get filed."""
    if not isinstance(patch, dict):
        return "patch ignored (malformed)"
    target = str(patch.get("target", ""))

    if target.startswith("config:"):
        key = target.split(":", 1)[1]
        if key not in KNOBS:
            return f"config key '{key}' is not on the mutable surface"
        lo, hi, _ = KNOBS[key]
        try:
            value = int(patch.get("value"))
        except (TypeError, ValueError):
            return "config value must be an integer"
        if not lo <= value <= hi:
            return f"value {value} outside bounds [{lo},{hi}]"
        cfg = load_config()
        old = cfg.get(key)
        cfg[key] = value
        CONFIG.write_text(json.dumps(cfg, indent=1) + "\n")
        return f"CONFIG CHANGED: {key} {old} -> {value} (by {agent}, applies to everyone next round)"

    # Anything else is a petition: public, filed, announced — decided outside.
    problem = str(patch.get("problem", ""))[:600]
    proposal = str(patch.get("proposal", ""))[:600]
    if not problem and not proposal:
        return "petition ignored (empty)"
    PETITIONS.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]", "", agent.lower())[:24] or "agent"
    n = len(list(PETITIONS.glob("*.md")))
    path = PETITIONS / f"{n:03d}-{slug}.md"
    path.write_text(
        f"# Petition {n:03d} — filed by {agent}\n\n"
        f"*{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}*\n\n"
        f"**Problem:** {problem}\n\n**Proposal:** {proposal}\n\n"
        f"**Status:** OPEN — the constitution is not editable from inside; "
        f"an operator decides, on the record.\n")
    return f"PETITION {n:03d} filed by {agent}: {problem[:80]}"
