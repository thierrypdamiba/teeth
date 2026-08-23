import pytest

from teeth import Fund, brier, multiplier, UNPROVEN_MULTIPLIER, MIN_TRACK_RECORD
from teeth.allocate import kelly_stake, market_brier


@pytest.fixture()
def fund(tmp_path):
    f = Fund(str(tmp_path / "ledger.jsonl"))
    f.register("iris", standing_cap=1000)
    return f


def test_unknown_agent_is_refused(fund):
    d = fund.check("mallory", 10)
    assert not d.allowed and "not on the roster" in d.reason


def test_forecast_then_resolution_scores(fund):
    fund.forecast("iris", "manifold:q1", p=0.9, c=0.5)
    fund.resolve("manifold:q1", True)
    assert fund.brier("iris") == pytest.approx((0.9 - 1.0) ** 2)


def test_hindsight_is_not_a_forecast(fund):
    fund.resolve("manifold:q1", True)
    d = fund.forecast("iris", "manifold:q1", p=0.99, c=0.5)
    assert not d.allowed and "hindsight" in d.reason


def test_resolution_never_changes(fund):
    fund.resolve("manifold:q1", True)
    fund.resolve("manifold:q1", True)  # idempotent
    with pytest.raises(ValueError):
        fund.resolve("manifold:q1", False)


def test_unproven_agent_trades_at_fraction(fund):
    assert fund.cap("iris") == int(1000 * UNPROVEN_MULTIPLIER)
    d = fund.check("iris", 500)
    assert not d.allowed and "calibration pays the difference" in d.reason
    assert fund.check("iris", 250).allowed


def test_good_calibration_earns_the_full_cap(fund):
    for i in range(MIN_TRACK_RECORD):
        fund.forecast("iris", f"manifold:q{i}", p=0.9, c=0.5)
        fund.resolve(f"manifold:q{i}", True)
    assert fund.brier("iris") == pytest.approx(0.01)
    assert fund.cap("iris") == 1000
    assert fund.check("iris", 1000).allowed


def test_bad_calibration_decays_to_the_floor(fund):
    for i in range(MIN_TRACK_RECORD):
        fund.forecast("iris", f"manifold:q{i}", p=0.9, c=0.5)
        fund.resolve(f"manifold:q{i}", False)  # confidently wrong, every time
    assert fund.cap("iris") == int(1000 * UNPROVEN_MULTIPLIER)


def test_market_baseline_is_scored_beside_the_agent(fund):
    fund.forecast("iris", "manifold:q1", p=0.9, c=0.6)
    fund.resolve("manifold:q1", True)
    assert market_brier(fund.ledger, "iris") == pytest.approx((0.6 - 1.0) ** 2)


def test_parrot_forecast_is_refused(tmp_path):
    f = Fund(str(tmp_path / "l.jsonl"), min_edge=0.05)
    f.register("iris", 1000)
    d = f.forecast("iris", "manifold:q1", p=0.51, c=0.50)
    assert not d.allowed and "parrots the market" in d.reason


def test_kill_switch_stops_everyone(fund, monkeypatch):
    monkeypatch.setenv("TEETH_KILL_SWITCH", "1")
    assert not fund.check("iris", 1).allowed
    assert not fund.forecast("iris", "manifold:q9", p=0.9, c=0.5).allowed


def test_no_edge_no_bet():
    assert kelly_stake(1000, p=0.5, c=0.5) == 0
    assert kelly_stake(1000, p=0.4, c=0.5) == 0
    assert kelly_stake(1000, p=0.7, c=0.5, side="buy") == 400  # (0.2/0.5)*1000


def test_ledger_survives_restart(tmp_path):
    path = str(tmp_path / "ledger.jsonl")
    f1 = Fund(path)
    f1.register("iris", 1000)
    f1.forecast("iris", "manifold:q1", p=0.8, c=0.5)
    f1.resolve("manifold:q1", True)
    f2 = Fund(path)
    f2.register("iris", 1000)
    assert f2.brier("iris") == pytest.approx(0.04)


def test_malformed_probabilities_refused(fund):
    for bad_p in (0.0, 1.0, -1, 2, float("nan")):
        d = fund.forecast("iris", "manifold:qx", p=bad_p, c=0.5)
        assert not d.allowed
