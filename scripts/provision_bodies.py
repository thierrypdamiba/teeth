#!/usr/bin/env python3
"""One body per soul: every mind on the board gets its own Maritime micro-VM.

Diffs the soul population (variants/*.md) against the Maritime fleet and
serially provisions a dedicated agent `soul-<name>` for each missing one —
serial with convergence because parallel creates starve the platform's build
worker (measured: 17/17 parallel failed, 17/17 serial succeeded). Generic
`lane-*` carriers get recycled to free seats when needed. On seat_limit it
reports loudly and stops — a degraded fleet announces itself.

Runs every marathon cycle; steady-state is a fast no-op. When an entrant
tweets a mind into the league, this is what mints their VM.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.maritime.sh/api"


def key() -> str | None:
    try:
        return json.load(open(Path.home() / ".config/maritime/credentials.json"))["api_key"]
    except Exception:
        return None


def req(k: str, path: str, method: str = "GET", body: dict | None = None, timeout: int = 20):
    r = urllib.request.Request(
        f"{API}{path}", method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw) if raw.strip() else {}


def converge(k: str, agent_id: str, checks: int = 6) -> bool:
    for _ in range(checks):
        time.sleep(25)
        try:
            st = req(k, f"/agents/{agent_id}").get("status")
        except Exception:
            continue
        if st in ("active", "sleeping"):
            return True
        if st == "error":
            try:
                req(k, f"/agents/{agent_id}/restart", "POST")
            except Exception:
                pass
    return False


def main() -> None:
    k = key()
    if not k:
        print("bodies: no maritime key — souls ride local")
        return
    souls = sorted(p.stem for p in (ROOT / "variants").glob("*.md"))
    try:
        fleet = req(k, "/agents")
    except Exception as e:
        print(f"bodies: maritime unreachable ({e})")
        return
    have = {a["name"] for a in fleet}
    missing = [s for s in souls if f"soul-{s}" not in have]
    if not missing:
        print(f"bodies: {len(souls)}/{len(souls)} souls embodied")
        return
    generics = [a for a in fleet if a["name"].startswith("lane-")]
    built = 0
    for s in missing:
        try:
            resp = req(k, "/agents", "POST", {"name": f"soul-{s}", "framework": "dsh"})
        except urllib.error.HTTPError as e:
            resp = {"code": "http_error", "detail": str(e)}
        agent = resp.get("agent") or resp
        if not agent.get("id"):
            if resp.get("code") == "seat_limit" and generics:
                victim = generics.pop()
                try:
                    req(k, f"/agents/{victim['id']}", "DELETE")
                    print(f"bodies: recycled {victim['name']} to free a seat")
                    resp = req(k, "/agents", "POST", {"name": f"soul-{s}", "framework": "dsh"})
                    agent = resp.get("agent") or resp
                except Exception:
                    pass
            if not agent.get("id"):
                print(f"bodies: SEAT LIMIT — {len(missing) - built} souls unembodied "
                      f"(upgrade the plan and they self-provision next cycle)")
                break
        if converge(k, agent["id"]):
            built += 1
            print(f"bodies: soul-{s} embodied")
        else:
            print(f"bodies: soul-{s} stuck in build — will retry next cycle")
    print(f"bodies: +{built} this cycle")


if __name__ == "__main__":
    main()
