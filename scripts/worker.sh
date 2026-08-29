#!/bin/bash
# Container entrypoint: keep the arena running forever.
#
# The ledger is the product and it lives in git, so the worker must be able to
# push. It clones fresh on boot rather than trusting a baked-in copy, so a
# restart always resumes from the published ledger instead of replaying a
# stale one — the ledger is append-only, and a fork of it is worse than a gap.
set -euo pipefail

: "${MARITIME_API_KEY:?set MARITIME_API_KEY}"
: "${GITHUB_TOKEN:?set GITHUB_TOKEN (needs contents:write on the repo)}"
REPO="${TEETH_REPO:-thierrypdamiba/teeth}"
BRANCH="${TEETH_BRANCH:-main}"
TICKS="${TEETH_TICKS_PER_CYCLE:-32}"

cd /arena
git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"
git config user.name  "${GIT_AUTHOR_NAME}"
git config user.email "${GIT_AUTHOR_EMAIL}"

while true; do
  echo "[worker] syncing $BRANCH"
  git fetch -q origin "$BRANCH" && git reset -q --hard "origin/$BRANCH"

  echo "[worker] marathon: $TICKS ticks at ${TEETH_TICK_SECONDS}s cadence"
  set +e
  ./scripts/marathon.sh "$TICKS"
  code=$?
  set -e

  # 3 is the budget fuse. Backing off hard is the point: a drained balance
  # is not a transient error, and hammering it just fills the log.
  if [ "$code" -eq 3 ]; then
    echo "[worker] LLM budget exhausted — sleeping 1h before retry"
    sleep 3600
  else
    echo "[worker] cycle finished (exit $code) — resyncing"
    sleep 15
  fi
done
