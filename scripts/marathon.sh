#!/bin/zsh
# The marathon: autonomous selection generations until stopped (or MAX_CYCLES).
# Each cycle: mint a 5-min pulse -> all variants forecast (real headless
# sessions) -> resolve everything due -> render the board -> push.
# Usage: ./scripts/marathon.sh [max_cycles]
set -u
cd "$(dirname "$0")/.."
MAX=${1:-40}
for i in $(seq 1 $MAX); do
  echo "── cycle $i/$MAX ── $(date -u +%H:%M:%SZ)"
  uv run python examples/rsi_loop.py mint
  sleep 330   # horizon (300s) + margin so the question is due
  uv run python examples/rsi_loop.py resolve
  git add ledger.jsonl docs/data.json 2>/dev/null
  git commit -q -m "pulse: generation $i resolved (autonomous marathon)" 2>/dev/null \
    && git push -q 2>/dev/null && echo "pushed gen $i" || echo "nothing to push"
done
echo "marathon complete: $MAX cycles"
