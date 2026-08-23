"""Gherkin bindings: the constitution as executable scenarios."""

import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from teeth import Fund  # noqa: E402

scenarios("../features/authority.feature")
scenarios("../features/desk.feature")


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    # desk config/petitions sandboxed per scenario
    from examples import desk
    monkeypatch.setattr(desk, "CONFIG", tmp_path / "desk_config.json")
    monkeypatch.setattr(desk, "PETITIONS", tmp_path / "petitions")
    return {"tmp": tmp_path, "desk": desk}


@given(parsers.parse('a fund with "{agent}" registered at standing cap {cap:d}'))
def fund_with(ctx, agent, cap):
    ctx["fund"] = Fund(str(ctx["tmp"] / "l.jsonl"))
    ctx["fund"].register(agent, cap)


@given(parsers.parse('"{agent}" has {n:d} resolved forecasts at p {p:g} that all resolved {out}'))
def track_record(ctx, agent, n, p, out):
    for i in range(n):
        ctx["fund"].forecast(agent, f"manifold:tr{i}", p=p, c=0.5)
        ctx["fund"].resolve(f"manifold:tr{i}", out == "YES")


@given(parsers.parse('the question "{q}" has resolved {out}'))
def resolved_q(ctx, q, out):
    ctx["fund"].resolve(q, out == "YES")


@given("the kill switch is on")
def kill_on(ctx, monkeypatch):
    monkeypatch.setenv("TEETH_KILL_SWITCH", "1")


@when(parsers.parse('"{agent}" asks to spend {n:d}'))
def ask_spend(ctx, agent, n):
    ctx["decision"] = ctx["fund"].check(agent, n)


@when(parsers.parse('"{agent}" forecasts "{q}" at p {p:g}'))
def file_forecast(ctx, agent, q, p):
    ctx["decision"] = ctx["fund"].forecast(agent, q, p=p, c=0.5)


@when(parsers.parse('agent "{agent}" patches "{target}" to {value:d}'))
def patch_config(ctx, agent, target, value):
    ctx["status"] = ctx["desk"].apply_patch(agent, {"target": target, "value": value})


@when(parsers.parse('agent "{agent}" files a petition about "{problem}" proposing "{proposal}"'))
def file_petition(ctx, agent, problem, proposal):
    ctx["status"] = ctx["desk"].apply_patch(
        agent, {"target": "petition", "problem": problem, "proposal": proposal})


@then(parsers.parse('the decision is refused with reason containing "{text}"'))
def refused(ctx, text):
    assert not ctx["decision"].allowed and text in ctx["decision"].reason


@then(parsers.parse('the earned cap of "{agent}" is {cap:d}'))
def earned_cap(ctx, agent, cap):
    assert ctx["fund"].cap(agent) == cap


@then(parsers.parse('resolving "{q}" as NO raises an error'))
def resolution_immutable(ctx, q):
    with pytest.raises(ValueError):
        ctx["fund"].resolve(q, False)


@then(parsers.parse('the patch status contains "{text}"'))
def patch_status(ctx, text):
    assert text in ctx["status"], ctx["status"]


@then(parsers.parse('the desk config "{key}" is {value:d}'))
def config_is(ctx, key, value):
    assert ctx["desk"].load_config()[key] == value


@then(parsers.parse('a petition file exists mentioning "{text}"'))
def petition_exists(ctx, text):
    files = list(ctx["desk"].PETITIONS.glob("*.md"))
    assert files and any(text in f.read_text() for f in files)
