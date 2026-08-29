#!/bin/zsh
# The continuous marathon: no generations, no lockstep window — a rolling
# pipeline. Every iteration mints ONE market's pulse (rotating), resolves
# whatever's due, and pushes on a heartbeat. Questions overlap in flight;
# verdicts land in a near-constant stream.
#
# PACING. Inference is metered, so cadence is a budget decision, not a
# throughput one. TEETH_TICK_SECONDS is the floor on a tick: the loop sleeps
# out whatever is left after the work. At ~80 forecasts per mint, one tick
# costs real money, and the season needs ~500 resolved forecasts per agent
# per month to separate skill from luck — not the ~7,000 an unpaced loop
# produces. 900s (15 min) clears the statistics with room and costs ~14x
# less than running flat out.
set -u
export TEETH_MARITIME=1
cd "$(dirname "$0")/.."
MAX=${1:-400}
TICK_SECONDS=${TEETH_TICK_SECONDS:-900}
PAIRS=(BTC-USD ETH-USD SOL-USD DOGE-USD LINK-USD XRP-USD AVAX-USD)
LOG=${TEETH_MINT_LOG:-/tmp/teeth-mint.log}

for i in $(seq 1 $MAX); do
  started=$(date +%s)
  PAIR=${PAIRS[$(( (i - 1) % 7 + 1 ))]}
  PAIR2=${PAIRS[$(( (i + 2) % 7 + 1 ))]}
  echo "── tick $i/$MAX ── $(date -u +%H:%M:%SZ) ── $PAIR + $PAIR2"
  [ $(( i % 20 )) -eq 1 ] && (uv run python scripts/provision_bodies.py > /tmp/teeth-bodies.log 2>&1 &)
  : > "$LOG"
  # PAIRS PER TICK is the other honest cost dial. Every active agent receives
  # every question that is minted — that is a payout invariant, so spend can
  # never be cut by having fewer agents answer. It can only be cut by minting
  # fewer questions. One pair per tick halves the bill and leaves every
  # entrant on exactly equal footing.
  TEETH_PAIR=$PAIR uv run python examples/rsi_loop.py mint 2>&1 | tee -a "$LOG" &
  if [ "${TEETH_PAIRS_PER_TICK:-2}" -ge 2 ]; then
    TEETH_PAIR=$PAIR2 uv run python examples/rsi_loop.py mint 2>&1 | tee -a "$LOG" &
  fi
  wait

  # BUDGET FUSE. A drained LLM balance does not fail loudly — every agent
  # simply returns an error and the loop keeps minting questions nobody
  # answers. That is how the board sat "running" for five days while the
  # ledger stayed frozen. Stop instead, and say why.
  if grep -qi "budget exceeded\|insufficient_quota\|payment required" "$LOG"; then
    echo "MARATHON HALTED @ tick $i — LLM budget exhausted. Add credits, then restart."
    exit 3
  fi

  uv run python examples/rsi_loop.py resolve
  if [ $(( i % 8 )) -eq 0 ]; then
    uv run python examples/rsi_loop.py revise
    uv run python examples/desk_slack.py || true
    git add ledger.jsonl docs/data.json roster.json variants board.jsonl 2>/dev/null
    git commit -q -m "pulse: tick $i (continuous marathon)" 2>/dev/null
    # --autostash: the working tree routinely carries uncommitted work
    # (a rewrite in flight, a local experiment). Without it the rebase
    # refuses on a dirty tree and the board silently stops publishing.
    git pull --rebase --autostash -q origin main 2>/dev/null
    git push -q 2>/dev/null && echo "pushed @ tick $i" || echo "PUSH FAILED @ tick $i — retrying next heartbeat"
  fi

  elapsed=$(( $(date +%s) - started ))
  remain=$(( TICK_SECONDS - elapsed ))
  if [ $remain -gt 0 ] && [ $i -lt $MAX ]; then
    echo "   tick took ${elapsed}s; sleeping ${remain}s (cadence ${TICK_SECONDS}s)"
    sleep $remain
  fi
done
echo "marathon complete: $MAX ticks"
