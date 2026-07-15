"""Tests for order_risk_gates.py — check_risk_gates() (Task 5E-6).

check_risk_gates() is pure composition of the five already-built,
already-reviewed gates from Tasks 5E-1 through 5E-5
(check_mrc_limit, check_cluster_variance, check_breaker_veto,
check_order_size, check_available_balance) — no new gate logic.

Per this task's brief, most tests mock each of the five gate functions
at the module's own references (order_risk_gates.check_mrc_limit, etc.)
rather than re-testing their internal logic — that is already covered
by 5E-1 through 5E-5's own test files. This file's job is to verify
orchestration: aggregation, fixed gate order/names, and the
at-most-once-each loading of risk_snapshot / thesis_breaker_state.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402
from order_risk_gates import check_risk_gates  # noqa: E402

GATE_NAMES = ["mrc", "cluster_variance", "breaker_veto", "size", "balance"]


def _order(side="BUY", ticker="CORZ", shares=10.0, price=100.0):
    return {"ticker": ticker, "side": side, "shares": shares, "price": price}


def _passing_gate(reason="OK"):
    return lambda *args, **kwargs: {"passed": True, "reason": reason}


def _failing_gate(reason="FAIL"):
    return lambda *args, **kwargs: {"passed": False, "reason": reason}


def _patch_all_gates(monkeypatch, **overrides):
    """Patch all 5 gate functions to pass by default; override specific ones."""
    defaults = {
        "check_mrc_limit": _passing_gate(),
        "check_cluster_variance": _passing_gate(),
        "check_breaker_veto": _passing_gate(),
        "check_order_size": _passing_gate(),
        "check_available_balance": _passing_gate(),
    }
    defaults.update(overrides)
    for name, fn in defaults.items():
        monkeypatch.setattr(order_risk_gates, name, fn)


def test_check_risk_gates_all_pass(monkeypatch):
    """All 5 gates mocked to pass -> passed=True, reasons=[], 5 gate entries."""
    _patch_all_gates(monkeypatch)
    order = _order()

    result = check_risk_gates(order, {}, risk_snapshot={}, thesis_breaker_state={})

    assert result["passed"] is True
    assert result["reasons"] == []
    assert len(result["gates"]) == 5


def test_check_risk_gates_one_gate_fails(monkeypatch):
    """Only check_mrc_limit fails -> overall passed=False, reasons has just that one."""
    _patch_all_gates(monkeypatch, check_mrc_limit=_failing_gate("MRC exceeded"))
    order = _order()

    result = check_risk_gates(order, {}, risk_snapshot={}, thesis_breaker_state={})

    assert result["passed"] is False
    assert result["reasons"] == ["MRC exceeded"]
    mrc_entry = next(g for g in result["gates"] if g["name"] == "mrc")
    assert mrc_entry["passed"] is False


def test_check_risk_gates_multiple_gates_fail(monkeypatch):
    """Two gates fail with distinct reasons -> both surface in reasons, in fixed gate order."""
    _patch_all_gates(
        monkeypatch,
        check_cluster_variance=_failing_gate("Cluster variance too high"),
        check_available_balance=_failing_gate("Insufficient cash"),
    )
    order = _order()

    result = check_risk_gates(order, {}, risk_snapshot={}, thesis_breaker_state={})

    assert result["passed"] is False
    assert result["reasons"] == ["Cluster variance too high", "Insufficient cash"]


def test_check_risk_gates_loads_risk_snapshot_once_shared_across_mrc_and_cluster(monkeypatch):
    """_load_risk_snapshot() is called exactly once, even though both MRC and
    cluster-variance gates need risk_snapshot."""
    calls = []

    def fake_load_risk_snapshot():
        calls.append(1)
        return {"marker": "snap"}

    monkeypatch.setattr(order_risk_gates, "_load_risk_snapshot", fake_load_risk_snapshot)
    _patch_all_gates(monkeypatch)
    order = _order()

    check_risk_gates(order, {}, thesis_breaker_state={})

    assert len(calls) == 1


def test_check_risk_gates_loads_thesis_breaker_state_once(monkeypatch):
    """_load_thesis_breaker_state() is called exactly once."""
    calls = []

    def fake_load_breaker_state():
        calls.append(1)
        return {"marker": "breaker"}

    monkeypatch.setattr(order_risk_gates, "_load_thesis_breaker_state", fake_load_breaker_state)
    _patch_all_gates(monkeypatch)
    order = _order()

    check_risk_gates(order, {}, risk_snapshot={})

    assert len(calls) == 1


def test_check_risk_gates_does_not_load_when_explicitly_supplied(monkeypatch):
    """risk_snapshot={} and thesis_breaker_state={} passed explicitly -> the
    loader helpers are never called."""

    def _never_call():
        raise AssertionError("loader helper should not have been called")

    monkeypatch.setattr(order_risk_gates, "_load_risk_snapshot", _never_call)
    monkeypatch.setattr(order_risk_gates, "_load_thesis_breaker_state", _never_call)
    _patch_all_gates(monkeypatch)
    order = _order()

    result = check_risk_gates(order, {}, risk_snapshot={}, thesis_breaker_state={})

    assert result["passed"] is True


def test_check_risk_gates_calls_each_gate_with_correct_args(monkeypatch):
    """Confirms no argument-shape mixup across the five different gate signatures:
    size gets daily_volume, balance gets questrade_cash, mrc/cluster share the
    SAME risk_snapshot object, breaker_veto gets thesis_breaker_state."""
    received = {}
    sentinel_snapshot = {"sentinel": "snapshot"}
    sentinel_breaker_state = {"sentinel": "breaker"}

    def fake_mrc(order, portfolio_state, risk_snapshot=None, **kwargs):
        received["mrc_risk_snapshot"] = risk_snapshot
        return {"passed": True, "reason": "OK"}

    def fake_cluster(order, portfolio_state, risk_snapshot=None, **kwargs):
        received["cluster_risk_snapshot"] = risk_snapshot
        return {"passed": True, "reason": "OK"}

    def fake_breaker(order, thesis_breaker_state=None, **kwargs):
        received["breaker_thesis_breaker_state"] = thesis_breaker_state
        return {"passed": True, "reason": "OK"}

    def fake_size(order, daily_volume=None, **kwargs):
        received["size_daily_volume"] = daily_volume
        return {"passed": True, "reason": "OK"}

    def fake_balance(order, questrade_cash=None, **kwargs):
        received["balance_questrade_cash"] = questrade_cash
        return {"passed": True, "reason": "OK"}

    _patch_all_gates(
        monkeypatch,
        check_mrc_limit=fake_mrc,
        check_cluster_variance=fake_cluster,
        check_breaker_veto=fake_breaker,
        check_order_size=fake_size,
        check_available_balance=fake_balance,
    )
    order = _order()
    portfolio_state = {"holdings": {}}

    check_risk_gates(
        order,
        portfolio_state,
        risk_snapshot=sentinel_snapshot,
        thesis_breaker_state=sentinel_breaker_state,
        daily_volume=12345.0,
        questrade_cash=6789.0,
    )

    assert received["mrc_risk_snapshot"] is sentinel_snapshot
    assert received["cluster_risk_snapshot"] is sentinel_snapshot
    assert received["breaker_thesis_breaker_state"] is sentinel_breaker_state
    assert received["size_daily_volume"] == 12345.0
    assert received["balance_questrade_cash"] == 6789.0


def test_check_risk_gates_gates_list_has_fixed_order_and_names(monkeypatch):
    """gates list is always in the order mrc, cluster_variance, breaker_veto, size, balance."""
    _patch_all_gates(monkeypatch)
    order = _order()

    result = check_risk_gates(order, {}, risk_snapshot={}, thesis_breaker_state={})

    assert [g["name"] for g in result["gates"]] == GATE_NAMES


def test_check_risk_gates_never_raises_when_a_gate_raises(monkeypatch):
    """Design decision (documented in the report): every one of the five real
    gates already 'never raises' per their own docstrings/tests (5E-1..5E-5),
    matching Task 5D-7's own precedent (get_validated_data_window()) of NOT
    adding a defensive try/except around already-'never raises' composed
    functions. check_risk_gates() therefore does not catch — a gate raising
    is a genuine regression in that gate's own contract, and should surface
    loudly (as an exception) rather than being silently swallowed into a
    misleading passed=True/False result. This test locks in that behavior:
    a raising gate propagates out of check_risk_gates() unmodified.
    """

    def _raising_gate(*args, **kwargs):
        raise ValueError("simulated gate failure")

    _patch_all_gates(monkeypatch, check_mrc_limit=_raising_gate)
    order = _order()

    try:
        check_risk_gates(order, {}, risk_snapshot={}, thesis_breaker_state={})
        raised = False
    except ValueError:
        raised = True

    assert raised is True
