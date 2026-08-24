#!/bin/zsh
# Sidecar publisher: keep the public data.json fresh between marathon ticks.
# Renders from the live ledger and pushes ONLY docs/data.json, ~every 45s.
# Never uses reset --hard: the working tree carries uncommitted ledger appends.
cd "$(dirname "$0")/.."
while true; do
  if [ -f .git/index.lock ]; then sleep 5; continue; fi
  uv run python scripts/render.py ledger.jsonl roster.json > /dev/null 2>&1
  if ! git diff --quiet -- docs/data.json; then
    git add docs/data.json && git commit -q -m "pulse: sidecar publish" > /dev/null 2>&1
    if git pull --rebase --autostash -q origin main > /dev/null 2>&1; then
      git push -q origin main > /dev/null 2>&1
    else
      git rebase --abort > /dev/null 2>&1
      git reset -q HEAD~1 > /dev/null 2>&1   # drop only our commit; files stay
    fi
  fi
  sleep 15
done
