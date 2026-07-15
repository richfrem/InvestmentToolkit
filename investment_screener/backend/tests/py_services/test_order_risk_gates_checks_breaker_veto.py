"""Tests for order_risk_gates.py — check_breaker_veto() (Task 5E-3).

This gate reads the REAL data/thesis_breaker_state.json (Phase 3 B5,
machine-owned by thesis_breakers.py) — NEVER target-portfolio.json,
which only stores human-authored breaker DEFINITIONS, never live
triggered/OK status. A breaker is TRIGGERED iff its "status" field is
the literal string "TRIGGERED", matching rebalancer.py's real
compute_breaker_warnings() (Phase 3 E2) check exactly.

Unlike E2's compute_breaker_warnings() (warn-only, never vetoes,
batch-shaped), this function returns a REAL veto for a single ad-hoc
order. SELL orders are never vetoed, matching E2's own real "buy
actions only" scope for the equivalent check.

thesis_breaker_state is passed explicitly in every test below — never
relies on the real file on disk.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402
from order_risk_gates import check_breaker_veto  # noqa: E402


def _order(ticker="CORZ", side="BUY"):
    return {"ticker": ticker, "side": side}


def _state(holdings):
    return {"holdings": holdings}


def test_check_breaker_veto_passes_when_no_breakers_triggered():
    """A ticker with breaker entries but all status='OK' passes."""
    order = _order(ticker="CORZ", side="BUY")
    state = _state({
        "CORZ": {
            "revenue_growth_floor": {"status": "OK", "currentValue": 0.25},
        }
    })

    result = check_breaker_veto(order, thesis_breaker_state=state)

    assert result["passed"] is True
    assert result["breaker"] is None


def test_check_breaker_veto_vetoes_when_breaker_triggered_for_buy():
    """A ticker with one status='TRIGGERED' breaker vetoes a BUY order."""
    order = _order(ticker="CORZ", side="BUY")
    state = _state({
        "CORZ": {
            "revenue_growth_floor": {"status": "TRIGGERED", "currentValue": 0.02},
        }
    })

    result = check_breaker_veto(order, thesis_breaker_state=state)

    assert result["passed"] is False
    assert result["breaker"] == "revenue_growth_floor"


def test_check_breaker_veto_sell_orders_never_vetoed():
    """A SELL order for a ticker with a TRIGGERED breaker always passes."""
    order = _order(ticker="CORZ", side="SELL")
    state = _state({
        "CORZ": {
            "revenue_growth_floor": {"status": "TRIGGERED", "currentValue": 0.02},
        }
    })

    result = check_breaker_veto(order, thesis_breaker_state=state)

    assert result["passed"] is True


def test_check_breaker_veto_handles_missing_state(monkeypatch, tmp_path):
    """thesis_breaker_state=None and no real file present: passed=True, no exception."""
    monkeypatch.setattr(order_risk_gates, "THESIS_BREAKER_STATE_PATH", tmp_path / "nonexistent.json")

    order = _order(ticker="CORZ", side="BUY")

    result = check_breaker_veto(order, thesis_breaker_state=None)

    assert result["passed"] is True


def test_check_breaker_veto_ticker_with_no_breaker_entries():
    """A ticker entirely absent from thesis_breaker_state['holdings'] passes."""
    order = _order(ticker="NEWCO", side="BUY")
    state = _state({
        "CORZ": {
            "revenue_growth_floor": {"status": "TRIGGERED", "currentValue": 0.02},
        }
    })

    result = check_breaker_veto(order, thesis_breaker_state=state)

    assert result["passed"] is True
    assert result["breaker"] is None


def test_check_breaker_veto_multiple_triggered_breakers_returns_one():
    """A ticker with TWO TRIGGERED breakers vetoes, surfacing exactly one breaker id."""
    order = _order(ticker="CORZ", side="BUY")
    state = _state({
        "CORZ": {
            "revenue_growth_floor": {"status": "TRIGGERED", "currentValue": 0.02},
            "margin_floor": {"status": "TRIGGERED", "currentValue": -0.10},
        }
    })

    result = check_breaker_veto(order, thesis_breaker_state=state)

    assert result["passed"] is False
    assert result["breaker"] in ("revenue_growth_floor", "margin_floor")


def test_check_breaker_veto_only_status_triggered_counts():
    """A breaker with status='WATCH' (or any non-'TRIGGERED' string) does not veto."""
    order = _order(ticker="CORZ", side="BUY")
    state = _state({
        "CORZ": {
            "revenue_growth_floor": {"status": "WATCH", "currentValue": 0.08},
        }
    })

    result = check_breaker_veto(order, thesis_breaker_state=state)

    assert result["passed"] is True
    assert result["breaker"] is None


def test_check_breaker_veto_reason_includes_breaker_id_and_ticker():
    """The reason string contains both the breaker id and the ticker."""
    order = _order(ticker="CORZ", side="BUY")
    state = _state({
        "CORZ": {
            "revenue_growth_floor": {"status": "TRIGGERED", "currentValue": 0.02},
        }
    })

    result = check_breaker_veto(order, thesis_breaker_state=state)

    assert "revenue_growth_floor" in result["reason"]
    assert "CORZ" in result["reason"]


def test_check_breaker_veto_never_raises_on_malformed_state():
    """Missing 'holdings' key, or a breaker entry that isn't a dict: passed=True, no exception."""
    order = _order(ticker="CORZ", side="BUY")

    result_no_holdings = check_breaker_veto(order, thesis_breaker_state={})
    assert result_no_holdings["passed"] is True

    state_bad_entry = _state({"CORZ": {"revenue_growth_floor": "not-a-dict"}})
    result_bad_entry = check_breaker_veto(order, thesis_breaker_state=state_bad_entry)
    assert result_bad_entry["passed"] is True
