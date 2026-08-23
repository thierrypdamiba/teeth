#!/usr/bin/env python3
"""Deploy a guest agent from anywhere — CLI twin of the issue intake.

    python3 scripts/deploy_agent.py <name> <personality...> --by <handle>

Same guardrails as the issue path (slug names, length caps, guest ceiling,
tools-disabled banner); this is the entry point the tweet relay uses.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("personality", nargs="+")
    ap.add_argument("--by", default="the-mortal-world")
    args = ap.parse_args()

    os.environ["ISSUE_BODY"] = (
        f"### Agent name\n\n{args.name}\n\n"
        f"### Personality and method\n\n{' '.join(args.personality)}\n")
    os.environ["ISSUE_USER"] = args.by
    import deploy_agent_from_issue
    deploy_agent_from_issue.main()


if __name__ == "__main__":
    main()
