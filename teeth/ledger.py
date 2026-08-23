"""The append-only forecast ledger. JSONL on purpose: greppable, diffable,
auditable with eyes. Two record kinds: forecast and resolution."""

import json
import os
import time
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Forecast:
    agent: str
    question: str  # e.g. "manifold:us-recession-in-2026"
    p: float       # the agent's probability the question resolves YES
    c: float       # the market's price when the forecast was made — never agent-supplied in governed use
    ts: float      # unix seconds

    def validate(self) -> None:
        if not isinstance(self.agent, str) or not self.agent:
            raise ValueError("agent must be a non-empty string")
        if not isinstance(self.question, str) or not self.question:
            raise ValueError("question must be a non-empty string")
        for name, v in (("p", self.p), ("c", self.c)):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(f"{name} must be a number, got {type(v).__name__}")
            if not 0.0 < float(v) < 1.0:
                raise ValueError(f"{name} must be strictly between 0 and 1, got {v}")


class Ledger:
    """Forecasts in, resolutions in, nothing ever out. Rebuilt from disk on
    every construction — the file is the state, the object is a view."""

    def __init__(self, path: str):
        self.path = path
        self.forecasts: list[Forecast] = []
        self.outcomes: dict[str, bool] = {}
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec["kind"] == "forecast":
                        self.forecasts.append(Forecast(
                            rec["agent"], rec["question"], rec["p"], rec["c"], rec["ts"]))
                    elif rec["kind"] == "resolution":
                        self.outcomes[rec["question"]] = bool(rec["outcome"])

    def _append(self, rec: dict) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    def record_forecast(self, fc: Forecast) -> None:
        fc.validate()
        if fc.question in self.outcomes:
            raise ValueError(f"{fc.question} already resolved — hindsight is not a forecast")
        self._append({"kind": "forecast", **asdict(fc)})
        self.forecasts.append(fc)

    def record_resolution(self, question: str, outcome: bool) -> None:
        if not isinstance(outcome, bool):
            raise ValueError(f"outcome must be a bool, got {type(outcome).__name__}")
        if question in self.outcomes:
            if self.outcomes[question] != outcome:
                raise ValueError(f"{question} already resolved {self.outcomes[question]}; "
                                 "a resolution never changes")
            return  # idempotent re-resolution
        self._append({"kind": "resolution", "question": question,
                      "outcome": outcome, "ts": time.time()})
        self.outcomes[question] = outcome

    def resolved_forecasts(self, agent: str) -> list[tuple[Forecast, bool]]:
        return [(fc, self.outcomes[fc.question]) for fc in self.forecasts
                if fc.agent == agent and fc.question in self.outcomes]
