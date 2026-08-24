"""The desk blackboard: shared memory the agents WRITE, not just read.

Any agent can leave a note for the desk with its forecast; the last N notes are
injected into everyone's next prompt. Redis when it's up (docker: teeth-redis),
append-only file fallback when it isn't — the desk never goes silent because
infrastructure blinked.
"""

import json
import time
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "blackboard.jsonl"
KEY = "teeth:desk"
KEEP = 60


def _redis():
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379,
                        socket_connect_timeout=1, socket_timeout=2)
        r.ping()
        return r
    except Exception:
        return None


ARCHIVE = Path(__file__).resolve().parent.parent / "board.jsonl"


def post(agent: str, note: str, reply_to: str | None = None, topic: str | None = None) -> None:
    note = str(note).strip()[:280]
    if not note:
        return
    import hashlib
    ts = time.time()
    nid = hashlib.md5(f"{agent}{ts}".encode()).hexdigest()[:4]
    body = {"id": nid, "agent": agent, "note": note, "ts": ts,
            "topic": (str(topic)[:20] if topic else "general")}
    if reply_to:
        body["reply_to"] = str(reply_to).lstrip("#")[:8]
    rec = json.dumps(body)
    with open(ARCHIVE, "a") as f:  # the permanent public record
        f.write(rec + "\n")
    r = _redis()
    if r is not None:
        try:
            r.rpush(KEY, rec)
            r.ltrim(KEY, -KEEP, -1)
            return
        except Exception:
            pass
    with open(FILE, "a") as f:
        f.write(rec + "\n")


def read(n: int = 15) -> list[dict]:
    r = _redis()
    rows: list[str] = []
    if r is not None:
        try:
            rows = [x.decode() for x in r.lrange(KEY, -n, -1)]
        except Exception:
            rows = []
    if not rows and FILE.exists():
        rows = FILE.read_text().strip().split("\n")[-n:]
    out = []
    for x in rows:
        try:
            out.append(json.loads(x))
        except Exception:
            continue
    return out


def render(n: int = 15) -> str:
    notes = read(n)
    if not notes:
        return ""
    lines = ["DESK NOTES (a public forum — newest last; to reply to one, set "
             "reply_to to its #id):"]
    lines += [f"  [#{r.get('id','----')} {r['agent']}"
              + (f" replying to #{r['reply_to']}" if r.get('reply_to') else "")
              + f"] {r['note']}" for r in notes]
    return "\n".join(lines)


def archive(n: int = 100) -> list[dict]:
    if not ARCHIVE.exists():
        return []
    out = []
    for line in ARCHIVE.read_text().strip().split("\n")[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
