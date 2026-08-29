from datetime import timezone

from teeth import Fund
from teeth.pulse import mint, parse, resolve_due


def test_parse_roundtrip():
    q = "pulse:BTC-USD>=63512.34@2026-08-23T22:30:00Z"
    pair, strike, deadline = parse(q)
    assert pair == "BTC-USD" and strike == 63512.34
    assert deadline.tzinfo == timezone.utc


def test_unparseable_is_ignored():
    assert parse("manifold:some-question") is None


def test_resolve_refuses_early(tmp_path, monkeypatch):
    f = Fund(str(tmp_path / "l.jsonl"))
    f.register("iris", 1000)
    # Deadline far in the future — must NOT resolve, even with a live print.
    q = "pulse:BTC-USD>=1.00@2099-01-01T00:00:00Z"
    f.forecast("iris", q, p=0.9, c=0.5)
    monkeypatch.setattr("teeth.pulse.spot", lambda pair: 99999.0)
    assert resolve_due(f.ledger) == []


def test_resolve_due_from_the_print(tmp_path, monkeypatch):
    f = Fund(str(tmp_path / "l.jsonl"))
    f.register("iris", 1000)
    q = "pulse:BTC-USD>=100.00@2020-01-01T00:00:00Z"  # deadline long past
    f.forecast("iris", q, p=0.9, c=0.5)
    monkeypatch.setattr("teeth.pulse.spot", lambda pair: 150.0)
    assert resolve_due(f.ledger) == [(q, True)]
    assert f.brier("iris") is not None


def test_no_print_no_resolution(tmp_path, monkeypatch):
    f = Fund(str(tmp_path / "l.jsonl"))
    f.register("iris", 1000)
    f.forecast("iris", "pulse:BTC-USD>=100.00@2020-01-01T00:00:00Z", p=0.9, c=0.5)
    monkeypatch.setattr("teeth.pulse.spot", lambda pair: None)
    assert resolve_due(f.ledger) == []  # fail closed


# --- the strike must land ON spot, at every price scale -------------------
# Regression: a fixed 2-decimal strike rounded DOGE at $0.0934 down to $0.09,
# i.e. 3.6% in the money. All 25 DOGE pulses ever minted carried the identical
# strike and all 25 resolved YES: a free +0.25 Brier edge per question for any
# agent that answered 0.99, against a board whose best agent earned +1.13 in
# total. At-the-money is the entire premise; it has to hold for cheap coins.

PRICES = [79030.33, 2430.04, 93.78, 11.37, 1.47, 0.0934, 0.00001234, 8.12e-08]


def test_strike_is_at_the_money_at_every_price_scale(monkeypatch):
    for px in PRICES:
        monkeypatch.setattr("teeth.pulse.spot", lambda pair, _p=px: _p)
        q = mint("X-USD", horizon_s=300)
        strike = parse(q)[1]
        assert abs(strike / px - 1) < 1e-6, f"{px} minted a strike at {strike}"


def test_cheap_coin_is_not_rounded_into_the_money(monkeypatch):
    monkeypatch.setattr("teeth.pulse.spot", lambda pair: 0.0934)
    assert parse(mint("DOGE-USD", horizon_s=300))[1] == 0.0934


def test_distinct_prices_mint_distinct_strikes(monkeypatch):
    strikes = set()
    for px in (0.0931, 0.0934, 0.0939):
        monkeypatch.setattr("teeth.pulse.spot", lambda pair, _p=px: _p)
        strikes.add(parse(mint("DOGE-USD", horizon_s=300))[1])
    assert len(strikes) == 3  # 2 decimals collapsed all three to 0.09


def test_zero_or_missing_price_never_crashes_the_mint(monkeypatch):
    monkeypatch.setattr("teeth.pulse.spot", lambda pair: None)
    assert mint("DOGE-USD", horizon_s=300) is None
    monkeypatch.setattr("teeth.pulse.spot", lambda pair: 0.0)
    assert parse(mint("DOGE-USD", horizon_s=300))[1] == 0.0
