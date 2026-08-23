"""The governed loop: register → forecast → resolve → authority.

Deny-by-default throughout: unknown agents are refused, resolved questions
refuse new forecasts, parrot forecasts (no edge vs the market) are refused,
and authority is the standing cap shrunk by proven calibration — never grown
by promises. The kill switch outranks everything.
"""

import os
from dataclasses import dataclass

from . import allocate
from .ledger import Forecast, Ledger
import time

KILL_SWITCH_ENV = "TEETH_KILL_SWITCH"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    agent: str
    reason: str


def _kill_switch() -> bool:
    return os.environ.get(KILL_SWITCH_ENV, "").lower() in ("1", "true", "on")


class Fund:
    def __init__(self, ledger_path: str, *, min_edge: float = 0.0):
        self.ledger = Ledger(ledger_path)
        self.roster: dict[str, int] = {}
        self.min_edge = min_edge

    # ── roster ────────────────────────────────────────────────────────────
    def register(self, agent: str, standing_cap: int) -> None:
        if not isinstance(agent, str) or not agent:
            raise ValueError("agent must be a non-empty string")
        if not isinstance(standing_cap, int) or isinstance(standing_cap, bool) or standing_cap < 0:
            raise ValueError("standing_cap must be a non-negative int")
        self.roster[agent] = standing_cap

    # ── the loop ──────────────────────────────────────────────────────────
    def forecast(self, agent: str, question: str, p: float, c: float, thesis: str = "") -> Decision:
        """Record a forecast. `c` is the market's price at this moment — in
        governed deployments it comes from the venue at the gateway, never
        from the agent (an agent choosing its own benchmark would choose a
        flattering one)."""
        if _kill_switch():
            return Decision(False, agent, "kill switch")
        if agent not in self.roster:
            return Decision(False, agent, f"unknown agent {agent!r} — not on the roster")
        fc = Forecast(agent, question, float(p), float(c), time.time(), str(thesis)[:400])
        try:
            fc.validate()
        except ValueError as e:
            return Decision(False, agent, str(e))
        if self.min_edge > 0 and abs(fc.p - fc.c) < self.min_edge:
            return Decision(False, agent,
                            f"forecast parrots the market (|p-c| < {self.min_edge}) — no edge, no bet")
        try:
            self.ledger.record_forecast(fc)
        except ValueError as e:
            return Decision(False, agent, str(e))
        return Decision(True, agent, "recorded")

    def resolve(self, question: str, outcome: bool) -> None:
        """Resolution comes from the world, not from any participant."""
        self.ledger.record_resolution(question, outcome)

    # ── what calibration bought ───────────────────────────────────────────
    def brier(self, agent: str) -> float | None:
        return allocate.brier(self.ledger, agent)

    def cap(self, agent: str) -> int:
        """Effective authority: standing cap × proven calibration."""
        if agent not in self.roster:
            return 0
        return int(self.roster[agent] * allocate.multiplier(self.ledger, agent))

    def stake(self, agent: str, p: float, c: float, side: str = "buy") -> int:
        """Kelly-edge stake inside the earned cap. No edge, no bet."""
        return allocate.kelly_stake(self.cap(agent), p, c, side)

    def check(self, agent: str, notional: int) -> Decision:
        """Deny-by-default authorization for a spend of `notional`."""
        if _kill_switch():
            return Decision(False, agent, "kill switch")
        if agent not in self.roster:
            return Decision(False, agent, f"unknown agent {agent!r} — not on the roster")
        if not isinstance(notional, int) or isinstance(notional, bool) or notional <= 0:
            return Decision(False, agent, f"notional must be a positive int, got {notional!r}")
        cap = self.cap(agent)
        if notional > cap:
            return Decision(False, agent,
                            f"over earned authority: {notional} > {cap} "
                            f"(standing {self.roster[agent]}, calibration pays the difference)")
        return Decision(True, agent, f"within earned authority ({notional} <= {cap})")

    def leaderboard(self) -> list[dict]:
        """Agents ranked by earned authority, with the market baseline beside
        them — the honest comparison is agent-vs-market, not agent-vs-zero."""
        rows = []
        for agent in self.roster:
            resolved = len(self.ledger.resolved_forecasts(agent))
            rows.append({
                "agent": agent,
                "resolved": resolved,
                "brier": allocate.brier(self.ledger, agent),
                "market_brier": allocate.market_brier(self.ledger, agent),
                "multiplier": allocate.multiplier(self.ledger, agent),
                "standing_cap": self.roster[agent],
                "earned_cap": self.cap(agent),
            })
        return sorted(rows, key=lambda r: (-r["earned_cap"], r["agent"]))
