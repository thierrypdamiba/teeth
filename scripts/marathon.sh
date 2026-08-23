#!/bin/zsh
# The continuous marathon: no generations, no lockstep window — a rolling
# pipeline. Every iteration mints ONE market's pulse (rotating), resolves
# whatever's due, and pushes on a heartbeat. Questions overlap in flight;
# verdicts land in a near-constant stream. The mint itself (~30-45s of
# parallel inference) is the natural pacing — cadence equals think-speed.
set -u
cd "$(dirname "$0")/.."
MAX=${1:-400}
PAIRS=(BTC-USD ETH-USD SOL-USD DOGE-USD LINK-USD XRP-USD AVAX-USD)
for i in $(seq 1 $MAX); do
  PAIR=${PAIRS[$(( (i - 1) % 7 + 1 ))]}
  echo "── tick $i/$MAX ── $(date -u +%H:%M:%SZ) ── $PAIR"
  [ $(( i % 20 )) -eq 1 ] && uv run python scripts/provision_bodies.py
  TEETH_PAIR=$PAIR uv run python examples/rsi_loop.py mint
  uv run python examples/rsi_loop.py resolve
  if [ $(( i % 8 )) -eq 0 ]; then
    uv run python examples/rsi_loop.py revise
    uv run python examples/desk_slack.py || true
    git add ledger.jsonl docs/data.json roster.json variants 2>/dev/null
    git commit -q -m "pulse: tick $i (continuous marathon)" 2>/dev/null
    git pull --rebase -q origin main 2>/dev/null
    git push -q 2>/dev/null && echo "pushed @ tick $i" || echo "PUSH FAILED @ tick $i — retrying next heartbeat"
  fi
done
echo "marathon complete: $MAX ticks"
