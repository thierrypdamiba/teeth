#!/usr/bin/env python3
"""ForecastBench submission harness.

Generates a forecast set in ForecastBench's exact format from a question set.
Baseline strategy (validates the pipeline; the evolved harness replaces it):
  - market questions: imitate the market (forecast = freeze_datetime_value) —
    the strongest known zero-effort baseline, honest about what it is.
  - dataset questions: 0.5 at every resolution horizon (their own imputation
    value — the declared "we don't know yet" answer).

    python3 scripts/bench_submit.py bench/2026-08-16-llm.json \
        --org brise-de-mer --model "baseline (market-imitation + 0.5)"

Output: bench/<due_date>.<org>.<N>.json ready for their GCP bucket upload.
Coverage rule: >=95% of both question types or the model is excluded.
"""

import argparse
import json
from pathlib import Path

MARKET_SOURCES = {"manifold", "metaculus", "polymarket"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question_set")
    ap.add_argument("--org", default="brise-de-mer")
    ap.add_argument("--model", default="baseline (market-imitation + 0.5)")
    ap.add_argument("--n", type=int, default=0)
    args = ap.parse_args()

    qs = json.load(open(args.question_set))
    forecasts = []
    n_market = n_dataset = 0
    for q in qs["questions"]:
        if isinstance(q.get("id"), list):
            continue  # combination questions: retired from the bench, skip defensively
        if q["source"] in MARKET_SOURCES:
            try:
                p = float(q.get("freeze_datetime_value"))
            except (TypeError, ValueError):
                p = 0.5
            p = min(max(p, 0.01), 0.99)
            forecasts.append({"id": q["id"], "source": q["source"], "forecast": p,
                              "resolution_date": None,
                              "reasoning": "baseline: market price at freeze"})
            n_market += 1
        else:
            dates = q.get("resolution_dates")
            if isinstance(dates, str):
                dates = json.loads(dates.replace("'", '"'))
            for rd in (dates or []):
                forecasts.append({"id": q["id"], "source": q["source"], "forecast": 0.5,
                                  "resolution_date": rd,
                                  "reasoning": "baseline: uninformative prior"})
            n_dataset += 1

    out = {
        "organization": args.org,
        "model": args.model,
        "model_organization": args.org,
        "question_set": qs["question_set"],
        "forecasts": forecasts,
    }
    due = qs["forecast_due_date"]
    dest = Path(args.question_set).parent / f"{due}.{args.org}.{args.n}.json"
    dest.write_text(json.dumps(out, indent=1))
    total_q = len([q for q in qs["questions"] if not isinstance(q.get("id"), list)])
    print(f"wrote {dest}")
    print(f"coverage: {n_market} market + {n_dataset} dataset questions "
          f"({n_market + n_dataset}/{total_q} = "
          f"{100 * (n_market + n_dataset) / total_q:.1f}%), "
          f"{len(forecasts)} total forecast rows")


if __name__ == "__main__":
    main()
