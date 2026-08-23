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
  uv run python scripts/provision_bodies.py
  # Five instantly-resolving markets per generation, minted IN PARALLEL —
  # the cycle costs max(mint) instead of sum(mint).
  uv run python examples/rsi_loop.py mint &
  TEETH_PAIR=ETH-USD uv run python examples/rsi_loop.py mint &
  TEETH_PAIR=SOL-USD uv run python examples/rsi_loop.py mint &
  TEETH_PAIR=DOGE-USD uv run python examples/rsi_loop.py mint &
  TEETH_PAIR=LINK-USD uv run python examples/rsi_loop.py mint &
  wait
  sleep 330   # horizon (300s) + margin so the question is due
  uv run python examples/rsi_loop.py resolve
  # The pen is offered every generation; whether to take it is each agent's
  # own policy, and the board judges that policy like any other theory.
  uv run python examples/rsi_loop.py revise
  uv run python examples/desk_slack.py || true
  git add ledger.jsonl docs/data.json roster.json variants 2>/dev/null
  git commit -q -m "pulse: generation $i resolved (autonomous marathon)" 2>/dev/null
  # Rebase before push: guest-agent commits and Autolab merges land on origin
  # directly, and a frozen public ledger blinds every downstream consumer.
  git pull --rebase -q origin main 2>/dev/null
  git push -q 2>/dev/null && echo "pushed gen $i" || echo "PUSH FAILED gen $i — will retry next cycle"
done
echo "marathon complete: $MAX cycles"
