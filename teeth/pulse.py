"""Pulse questions: fast-resolving, self-verifying binaries for tight loops.

A pulse question is minted at-the-money — "will SPOT be >= its current price
at time T" — so the fair benchmark is 0.5 by construction: no market to quote,
no judge to game, and any consistent edge an agent shows is real skill.
Resolution is a price print from a public exchange API: exogenous, checkable
by anyone, and it arrives on the world's clock — just a much faster clock
than an election.

Question id format:  pulse:BTC-USD>=63512.34@2026-08-23T22:30:00Z
"""

import json
import re
import time
import urllib.request
from datetime import datetime, timezone

from .ledger import Ledger

_TIMEOUT = 10
_Q = re.compile(r"^pulse:([A-Z0-9-]+)>=([0-9.]+)@(.+Z)$")


def spot(pair: str = "BTC-USD") -> float | None:
    """Spot price. Crypto pairs (with a dash) come from Coinbase's public API;
    bare tickers (NVDA, SPY) from Alpaca's data API using ALPACA_PAPER_KEY /
    ALPACA_PAPER_SECRET from the environment. Fails closed either way."""
    import os
    try:
        if "-" in pair:
            req = urllib.request.Request(
                f"https://api.coinbase.com/v2/prices/{pair}/spot",
                headers={"User-Agent": "teeth/0.1"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                return float(json.load(r)["data"]["amount"])
        key, sec = os.environ.get("ALPACA_PAPER_KEY"), os.environ.get("ALPACA_PAPER_SECRET")
        if not key or not sec:
            return None
        req = urllib.request.Request(
            f"https://data.alpaca.markets/v2/stocks/{pair}/trades/latest",
            headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return float(json.load(r)["trade"]["p"])
    except Exception:
        return None


def equity_market_open() -> bool:
    """Alpaca's clock — equities pulse only while the market trades (a closed
    market makes the outcome a stale-print coin toss, which is noise, not a
    question). Fails closed."""
    import os
    key, sec = os.environ.get("ALPACA_PAPER_KEY"), os.environ.get("ALPACA_PAPER_SECRET")
    if not key or not sec:
        return False
    try:
        req = urllib.request.Request(
            "https://paper-api.alpaca.markets/v2/clock",
            headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return bool(json.load(r).get("is_open"))
    except Exception:
        return False


def mint(pair: str = "BTC-USD", horizon_s: int = 1800) -> str | None:
    """Mint an at-the-money pulse question resolving `horizon_s` from now."""
    px = spot(pair)
    if px is None:
        return None
    deadline = datetime.fromtimestamp(int(time.time()) + horizon_s, tz=timezone.utc)
    return f"pulse:{pair}>={px:.2f}@{deadline.strftime('%Y-%m-%dT%H:%M:%SZ')}"


def parse(question: str) -> tuple[str, float, datetime] | None:
    m = _Q.match(question)
    if not m:
        return None
    pair, strike, dl = m.groups()
    try:
        return pair, float(strike), datetime.strptime(dl, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def resolve_due(ledger: Ledger) -> list[tuple[str, bool]]:
    """Resolve every pulse question whose deadline has passed, from the live
    spot print. Returns what was resolved. Refuses to resolve early — the
    future is not consulted ahead of schedule."""
    now = datetime.now(timezone.utc)
    resolved = []
    open_qs = {fc.question for fc in ledger.forecasts if fc.question not in ledger.outcomes}
    for q in sorted(open_qs):
        parsed = parse(q)
        if parsed is None:
            continue
        pair, strike, deadline = parsed
        if now < deadline:
            continue
        px = spot(pair)
        if px is None:
            continue  # fail closed: no print, no resolution; try again later
        outcome = px >= strike
        ledger.record_resolution(q, outcome)
        resolved.append((q, outcome))
    return resolved
