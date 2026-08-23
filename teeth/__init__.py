"""teeth — evals with teeth.

Score agents on the future: they forecast live prediction markets, resolution
Brier-scores them, and calibration pays out as capped authority. A fitness
function that cannot be memorized, contaminated, or overfit — the questions
haven't resolved yet.

The loop:

    fund = Fund("ledger.jsonl")
    fund.register("iris", standing_cap=1000)
    fund.forecast("iris", "manifold:us-recession-in-2026", p=0.12, c=0.085)
    ...time passes, the world decides...
    fund.resolve("manifold:us-recession-in-2026", outcome=False)
    fund.cap("iris")            # authority, earned
    fund.check("iris", 500)     # deny-by-default authorization

Design rules, in order: fail closed, resolve externally, pay in authority.
No dependencies. The ledger is append-only JSONL you can read with your eyes.
"""

from .ledger import Forecast, Ledger
from .allocate import brier, multiplier, UNPROVEN_MULTIPLIER, MIN_TRACK_RECORD
from .fund import Decision, Fund
from . import markets

__version__ = "0.1.0"
__all__ = [
    "Fund", "Decision", "Ledger", "Forecast",
    "brier", "multiplier", "markets",
    "UNPROVEN_MULTIPLIER", "MIN_TRACK_RECORD",
]
