#!/usr/bin/env python3
"""A real LLM forecaster: a character file + a live market -> a forecast on the ledger.

Runs the character as a headless Claude session (works with Claude Code's
subscription auth — no API key needed). The agent sees the question and its own
mandate. It does NOT choose the benchmark: `c` is quoted from the venue here,
at forecast time, and the ledger records both.

    python3 examples/character_agent.py <character.md> <agent> <venue:slug> \
        [--ledger ledger.jsonl] [--roster roster.json]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from teeth import Fund, markets  # noqa: E402


def ask_character(character_md: str, question: str, market_context: str) -> dict:
    prompt = f"""You are the following colleague at an agent-native trading firm.
Stay in character; your mandate governs how you reason.

{character_md}

FORECASTING TASK
Question (binary, resolves YES/NO): {question}
{market_context}

Think through your mandate's method, then answer with ONLY a JSON object:
{{"p": <your probability of YES, strictly between 0 and 1>, "thesis": "<one sentence, in your voice, naming your reference class or signal>"}}
Do not restate the market's price as your probability — if you have no
independent view that differs from the market, say so by staying very close
to it and your stake will rightly be ~zero."""
    r = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"claude -p failed: {(r.stderr or r.stdout)[:300]}")
    payload = json.loads(r.stdout)
    # claude -p --output-format json returns an envelope dict; some versions
    # return a list of records where the last carries the result.
    if isinstance(payload, list):
        payload = next((rec for rec in reversed(payload)
                        if isinstance(rec, dict) and "result" in rec), {})
    text = payload.get("result", "")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"no JSON in agent reply: {text[:200]}")
    return json.loads(text[start:end + 1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("agent")
    ap.add_argument("question")
    ap.add_argument("--ledger", default="ledger.jsonl")
    ap.add_argument("--roster", default="roster.json")
    args = ap.parse_args()

    c = markets.quote(args.question)
    if c is None:
        sys.exit(f"no live quote for {args.question} — refusing to invent a benchmark")

    character_md = Path(args.character).read_text()
    reply = ask_character(
        character_md, args.question,
        f"The market currently prices YES at {c:.3f}. "
        "(Recorded as your benchmark; you are scored on beating it.)")

    fund = Fund(args.ledger, min_edge=0.0)
    for agent, cap in json.load(open(args.roster)).items():
        fund.register(agent, cap)
    d = fund.forecast(args.agent, args.question, p=float(reply["p"]), c=c)
    print(json.dumps({"agent": args.agent, "question": args.question,
                      "p": reply.get("p"), "c": round(c, 4),
                      "thesis": reply.get("thesis"), "decision": d.reason}, indent=1))


if __name__ == "__main__":
    main()
