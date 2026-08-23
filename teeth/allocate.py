"""Calibration → authority. The scoring is textbook (Brier, 1950); the point
is what it feeds: capital, not a leaderboard."""

from .ledger import Ledger

# An agent with no resolved track record trades at a fraction of its standing
# cap. Skill is proven to the ledger, never asserted to the allocator.
UNPROVEN_MULTIPLIER = 0.25
MIN_TRACK_RECORD = 10

# Linear map from mean Brier to multiplier. 0.25 is a coin-flipper's Brier;
# 0.15 or better earns the full cap, 0.35 or worse decays to unproven.
_FULL_AT = 0.15
_FLOOR_AT = 0.35


def brier(ledger: Ledger, agent: str) -> float | None:
    """Mean Brier over resolved forecasts. None = no evidence, which callers
    must treat as unproven, never as perfect."""
    rows = ledger.resolved_forecasts(agent)
    if not rows:
        return None
    return sum((fc.p - (1.0 if out else 0.0)) ** 2 for fc, out in rows) / len(rows)


def market_brier(ledger: Ledger, agent: str) -> float | None:
    """The market's Brier over the same questions at the same moments — the
    honest baseline. An agent's edge is beating this, not beating zero."""
    rows = ledger.resolved_forecasts(agent)
    if not rows:
        return None
    return sum((fc.c - (1.0 if out else 0.0)) ** 2 for fc, out in rows) / len(rows)


def multiplier(ledger: Ledger, agent: str) -> float:
    rows = ledger.resolved_forecasts(agent)
    if len(rows) < MIN_TRACK_RECORD:
        return UNPROVEN_MULTIPLIER
    b = brier(ledger, agent)
    if b <= _FULL_AT:
        return 1.0
    if b >= _FLOOR_AT:
        return UNPROVEN_MULTIPLIER
    # Linear between the anchors.
    frac = (b - _FULL_AT) / (_FLOOR_AT - _FULL_AT)
    return round(1.0 - frac * (1.0 - UNPROVEN_MULTIPLIER), 4)


def edge(p: float, c: float, side: str = "buy") -> float:
    """The forecast's edge over the market for the given side. A forecast that
    parrots the price has no edge and, in governed use, no business trading."""
    return (p - c) if side == "buy" else (c - p)


def kelly_stake(cap: int, p: float, c: float, side: str = "buy") -> int:
    """Edge-proportional stake, capped. Kelly against the market price on a
    binary contract, floored at zero: no edge, no bet."""
    e = edge(p, c, side)
    if e <= 0:
        return 0
    denom = (1.0 - c) if side == "buy" else c
    if denom <= 0:
        return 0
    # Round to the nearest whole dollar rather than truncating: float artifacts
    # like 0.7-0.5=0.19999... would otherwise shave a dollar off clean edges.
    return min(cap, int(round(cap * (e / denom))))
