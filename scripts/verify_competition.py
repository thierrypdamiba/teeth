#!/usr/bin/env python3
"""Fail CI when a payout invariant is violated."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from teeth.competition import validate_registry  # noqa: E402


def verify_no_local_inference() -> None:
    governed = ROOT / "examples" / "rsi_loop.py"
    source = governed.read_text()
    tree = ast.parse(source, filename=str(governed))
    forbidden = {"ask_character", "_local_text"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in forbidden:
                raise ValueError(f"governed loop calls forbidden local inference: {node.func.id}")
        if isinstance(node, ast.Constant) and node.value == "claude":
            raise ValueError("governed loop contains a local Claude executable path")


def main() -> None:
    validate_registry(ROOT)
    verify_no_local_inference()
    print("competition invariants verified")


if __name__ == "__main__":
    main()
