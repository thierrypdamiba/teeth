#!/usr/bin/env python3
"""The school: an entrance exam before a variant touches the live board.

Inner-loop/outer-loop split: dense cheap practice, then sparse expensive
reality. The exam quizzes a candidate on the K most recently RESOLVED pulse
questions from this fund's own ledger — questions whose answers exist but
which the candidate is asked blind, with tools disabled (`--tools ""`) so it
cannot look anything up. Recent 5-minute price prints are past any model's
training data, so the only honest path to a good exam Brier is a good prior.

Pass bar: exam Brier <= 0.25 (a coin-flipper's score). This deliberately
admits the humble — an agent that knows it can't know and says 0.5 passes.
What the exam FAILS is confident wrongness, which is exactly what should
never reach live capital.

    python3 examples/entrance_exam.py variants/iris-momentum.md [--k 8]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teeth import Fund  # noqa: E402
from teeth.pulse import parse  # noqa: E402

PASS_BRIER = 0.25


def ask_blind(character_md: str, question: str) -> float:
    """One exam question, tools off — the candidate reasons, it cannot browse."""
    prompt = f"""{character_md}

EXAM QUESTION (binary; you have NO tools and NO data feeds — reason from your
method and priors only): {question}
The strike was at-the-money when minted, so the no-information answer is 0.5.
Reply with ONLY: {{"p": <probability of YES, strictly between 0 and 1>}}"""
    r = subprocess.run(["claude", "-p", prompt, "--output-format", "json", "--tools", ""],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"exam runner failed: {(r.stderr or r.stdout)[:200]}")
    payload = json.loads(r.stdout)
    if isinstance(payload, list):
        payload = next((x for x in reversed(payload) if isinstance(x, dict) and "result" in x), {})
    text = payload.get("result", "")
    return float(json.loads(text[text.find("{"):text.rfind("}") + 1])["p"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--ledger", default=str(ROOT / "ledger.jsonl"))
    args = ap.parse_args()

    fund = Fund(args.ledger)
    resolved_pulses = [(q, out) for q, out in fund.ledger.outcomes.items() if parse(q)]
    if len(resolved_pulses) < args.k:
        sys.exit(f"school not open yet: only {len(resolved_pulses)} resolved pulse "
                 f"questions on the ledger (need {args.k})")
    exam = resolved_pulses[-args.k:]

    character_md = Path(args.character).read_text()
    total = 0.0
    for q, outcome in exam:
        p = ask_blind(character_md, q)
        score = (p - (1.0 if outcome else 0.0)) ** 2
        total += score
        print(f"  {q}  ->  p={p:.2f}  actual={'YES' if outcome else 'NO'}  brier={score:.3f}")
    exam_brier = total / len(exam)
    verdict = "PASS — admitted to the live board" if exam_brier <= PASS_BRIER \
        else "FAIL — confident wrongness does not touch capital"
    print(f"\nexam brier {exam_brier:.3f} vs bar {PASS_BRIER}: {verdict}")
    sys.exit(0 if exam_brier <= PASS_BRIER else 1)


if __name__ == "__main__":
    main()
