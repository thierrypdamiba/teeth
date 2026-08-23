"""Live market quotes — the `c` an agent must beat, read from venues that
don't care about your feelings. Stdlib only; every failure fails closed
(returns None, and a governed caller refuses the forecast rather than
inventing a benchmark)."""

import json
import urllib.request

_TIMEOUT = 10


def _get(url: str) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "teeth/0.1"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return json.load(r)
    except Exception:
        return None  # fail closed: no quote is no quote


def manifold_prob(slug: str) -> float | None:
    """Probability from Manifold Markets by market slug."""
    d = _get(f"https://api.manifold.markets/v0/slug/{slug}")
    if isinstance(d, dict) and isinstance(d.get("probability"), (int, float)):
        p = float(d["probability"])
        return p if 0.0 < p < 1.0 else None
    return None


def polymarket_prob(slug: str) -> float | None:
    """YES price from Polymarket's public gamma API by market slug."""
    d = _get(f"https://gamma-api.polymarket.com/markets?slug={slug}")
    if isinstance(d, list) and d and isinstance(d[0], dict):
        prices = d[0].get("outcomePrices")
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except ValueError:
                return None
        if isinstance(prices, list) and prices:
            try:
                p = float(prices[0])
            except (TypeError, ValueError):
                return None
            return p if 0.0 < p < 1.0 else None
    return None


def quote(question: str) -> float | None:
    """Dispatch on a `venue:slug` question id."""
    venue, _, slug = question.partition(":")
    if not slug:
        return None
    return {"manifold": manifold_prob, "polymarket": polymarket_prob}.get(venue, lambda s: None)(slug)
