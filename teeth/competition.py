"""Prize-season registry and scoring.

Ownership and eligibility live in structured, validated data rather than in a
mutable agent prompt. The current public ledger can contain preseason and
house-control records; only registered entrants and resolutions inside the
declared UTC window can affect the purse.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,22}[a-z0-9]$")


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid UTC timestamp {value!r}") from exc
    return parsed


def load_config(root: Path) -> dict:
    return json.loads((root / "season.json").read_text())


def load_registry(root: Path) -> dict:
    return json.loads((root / "entrants.json").read_text())


def strategy_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_registry(root: Path) -> None:
    season = load_config(root)
    registry = load_registry(root)
    start = parse_utc(season["starts_at"])
    end = parse_utc(season["ends_at"])
    closes = parse_utc(season["registration_closes_at"])
    payout = parse_utc(season["payout_at"])
    if not closes <= start < end <= payout:
        raise ValueError("season timestamps must satisfy registration <= start < end <= payout")
    if registry.get("version") != 1 or registry.get("season_id") != season.get("id"):
        raise ValueError("entrant registry version or season id does not match season.json")
    entries = registry.get("entrants")
    if not isinstance(entries, dict):
        raise ValueError("entrants must be an object keyed by agent slug")
    if len(entries) > int(season["maximum_entrants"]):
        raise ValueError("entrant registry exceeds the season ceiling")

    identities: set[str] = set()
    issues: set[int] = set()
    for slug, entry in entries.items():
        if not SLUG.fullmatch(slug):
            raise ValueError(f"invalid entrant slug {slug!r}")
        identity = entry.get("identity_sha256")
        if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise ValueError(f"{slug}: invalid owner identity digest")
        if identity in identities:
            raise ValueError(f"{slug}: one GitHub identity may enter only one agent")
        identities.add(identity)
        issue = entry.get("issue_number")
        if not isinstance(issue, int) or issue <= 0 or issue in issues:
            raise ValueError(f"{slug}: invalid or duplicate source issue")
        issues.add(issue)
        submitted = parse_utc(entry.get("submitted_at"))
        if submitted >= closes:
            raise ValueError(f"{slug}: submitted after registration closed")
        source = root / "submissions" / season["id"] / f"{slug}.md"
        variant = root / "variants" / f"{slug}.md"
        if not source.is_file() or not variant.is_file():
            raise ValueError(f"{slug}: immutable submission or live variant is missing")
        if strategy_digest(source.read_text()) != entry.get("strategy_sha256"):
            raise ValueError(f"{slug}: immutable submission hash mismatch")


def active_agents(root: Path) -> list[str]:
    """Every registered entrant plus fixed controls receives every question."""
    validate_registry(root)
    season = load_config(root)
    registry = load_registry(root)
    entrants = [slug for slug, row in registry["entrants"].items()
                if row.get("eligible", True)]
    return sorted(set(season.get("controls", [])) | set(entrants))


def score_rows(ledger, root: Path) -> list[dict]:
    """Compute purse standings from the frozen UTC window and entrant set."""
    validate_registry(root)
    season = load_config(root)
    registry = load_registry(root)
    start = parse_utc(season["starts_at"]).timestamp()
    end = parse_utc(season["ends_at"]).timestamp()
    minimum = int(season["minimum_resolved"])
    scores = {slug: {"edge_sum": 0.0, "n": 0}
              for slug, row in registry["entrants"].items()
              if row.get("eligible", True)}
    for forecast in ledger.forecasts:
        if forecast.agent not in scores or forecast.question not in ledger.outcomes:
            continue
        resolved_at = ledger.resolution_times.get(forecast.question, 0.0)
        if not start <= resolved_at < end:
            continue
        outcome = 1.0 if ledger.outcomes[forecast.question] else 0.0
        scores[forecast.agent]["edge_sum"] += (
            (forecast.c - outcome) ** 2 - (forecast.p - outcome) ** 2
        )
        scores[forecast.agent]["n"] += 1
    rows = [
        {"agent": slug, "edge_sum": round(values["edge_sum"], 6),
         "n": values["n"], "qualified": values["n"] >= minimum}
        for slug, values in scores.items()
    ]
    return sorted(rows, key=lambda row: (-row["qualified"], -row["edge_sum"], row["agent"]))
