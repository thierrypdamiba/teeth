from datetime import timezone

from teeth import Fund
from teeth.pulse import parse, resolve_due


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
