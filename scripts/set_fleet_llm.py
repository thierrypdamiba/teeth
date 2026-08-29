#!/usr/bin/env python3
"""Set the inference backend for every body on the fleet, in one pass.

Inference is the season's only real running cost — ~80 forecasts land per
mint, and the model behind them decides whether a month costs $10 or $500.
That choice lives in three per-agent environment variables that dsh reads at
boot (see /opt/maritime/dsh-maritime.yml), so it is changeable without
touching the scoring constitution or redeploying anything:

    DSH_MODEL        which model answers
    OPENAI_BASE_URL  which provider serves it (Maritime's metered proxy by
                     default; point it elsewhere to bring your own billing)
    OPENAI_API_KEY   the credential for that provider

Examples
--------
    # cheaper model, still on Maritime's proxy and Maritime's billing
    python scripts/set_fleet_llm.py --model gpt-4o

    # bring your own provider — bypasses the Maritime LLM budget entirely
    python scripts/set_fleet_llm.py --model deepseek-chat \
        --base-url https://api.deepseek.com/v1 --api-key "$DEEPSEEK_API_KEY"

    # look before you leap
    python scripts/set_fleet_llm.py --model gpt-4o --dry-run

Stdlib only. Secrets are never printed.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.maritime.sh/api"
SECRET_KEYS = {"OPENAI_API_KEY"}


def key() -> str | None:
    k = os.environ.get("MARITIME_API_KEY") or os.environ.get("MARITIME_TOKEN")
    if k:
        return k
    try:
        return json.load(open(Path.home() / ".config/maritime/credentials.json"))["api_key"]
    except Exception:
        return None


def req(k: str, path: str, method: str = "GET", body: dict | None = None, timeout: int = 30):
    r = urllib.request.Request(
        f"{API}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
        return resp.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def set_var(k: str, agent_id: str, existing: set[str], name: str, value: str) -> str:
    """PUT updates an existing var; a var that does not exist yet needs POST."""
    payload = {"key": name, "value": value, "isSecret": name in SECRET_KEYS}
    if name in existing:
        status, _ = req(k, f"/agents/{agent_id}/env/{name}", "PUT", payload)
        if status in (200, 201, 204):
            return "updated"
    status, body = req(k, f"/agents/{agent_id}/env", "POST", payload)
    if status in (200, 201, 204):
        return "created"
    return f"FAILED({status})"


def main() -> None:
    ap = argparse.ArgumentParser(description="Set the fleet's inference backend.")
    ap.add_argument("--model", help="DSH_MODEL, e.g. gpt-4o or deepseek-chat")
    ap.add_argument("--base-url", help="OPENAI_BASE_URL (omit to stay on Maritime's proxy)")
    ap.add_argument("--api-key", help="OPENAI_API_KEY for that provider")
    ap.add_argument("--prefix", default="soul-", help="which bodies to touch (default: soul-)")
    ap.add_argument("--dry-run", action="store_true", help="show the plan, change nothing")
    args = ap.parse_args()

    if not (args.model or args.base_url or args.api_key):
        sys.exit("nothing to set — pass at least one of --model / --base-url / --api-key")

    k = key()
    if not k:
        sys.exit("no Maritime key (MARITIME_API_KEY or ~/.config/maritime/credentials.json)")

    status, fleet = req(k, "/agents")
    if not isinstance(fleet, list):
        sys.exit(f"could not list fleet: {status} {fleet}")
    targets = [a for a in fleet if str(a.get("name", "")).startswith(args.prefix)]

    plan = {n: v for n, v in (("DSH_MODEL", args.model),
                              ("OPENAI_BASE_URL", args.base_url),
                              ("OPENAI_API_KEY", args.api_key)) if v}
    shown = {n: ("<hidden>" if n in SECRET_KEYS else v) for n, v in plan.items()}
    print(f"{len(targets)} bodies matching {args.prefix!r}; setting {shown}")
    if args.dry_run:
        print("dry run — nothing changed")
        return

    ok = 0
    for a in targets:
        existing = {e["key"] for e in (req(k, f"/agents/{a['id']}/env")[1] or []) if isinstance(e, dict)}
        results = [set_var(k, a["id"], existing, n, v) for n, v in plan.items()]
        req(k, f"/agents/{a['id']}/reload-env", "POST")
        bad = [r for r in results if r.startswith("FAILED")]
        ok += not bad
        print(f"  {a['name']:<28} {', '.join(results)}")
    print(f"\n{ok}/{len(targets)} bodies updated. Bodies re-read env on next wake.")


if __name__ == "__main__":
    main()
