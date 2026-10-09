"""Tests for order_risk_gates.py — check_breaker_veto() (Task 5E-3).

This gate reads the evaluated breaker state from domain_model.sqlite
(thesis_breaker_state, written by thesis_breakers.py), never the breaker
DEFINITIONS, which carry no live triggered/OK status. A breaker is TRIGGERED iff its "status" field is
the literal string "TRIGGERED", matching rebalancer.py's real
compute_breaker_warnings() (Phase 3 E2) check exactly.

Unlike E2's compute_breaker_warnings() (warn-only, never vetoes,
batch-shaped), this function returns a REAL veto for a single ad-hoc
order. SELL orders are never vetoed, matching E2's own real "buy
actions only" scope for the equivalent check.

thesis_breaker_state is passed explicitly in most tests; the SQLite-backed
ones use a temporary database via db_path.
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


def _db_with_breaker(tmp_path, status="TRIGGERED", ticker="CORZ"):
    """A database holding one auto breaker for ``ticker`` whose evaluated state has the given status."""
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import resolve_investment, update_investment_fields
    from domain_model.thesis_breaker_repository import replace_breaker_state, upsert_breaker
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    update_investment_fields(conn, resolve_investment(conn, ticker), target_weight=3.0)
    upsert_breaker(conn, ticker, {"id": "rsi-low", "type": "auto", "metric": "rsi", "operator": "<", "threshold": 30, "horizon": 3})
    replace_breaker_state(conn, {ticker: {"rsi-low": {
        "type": "auto", "currentValue": 22.0, "conditionMet": True, "currentStreak": 3,
        "streakStartDate": "2026-10-07", "lastEvaluatedAt": "2026-10-09T00:00:00Z", "status": status}}})
    conn.close()
    return db_path


def test_check_breaker_veto_with_no_stored_state_passes(tmp_path):
    """state=None and an empty database: passed=True, no exception."""
    from domain_model.db_client import initialize_db
    db_path = tmp_path / "empty.sqlite"
    initialize_db(str(db_path)).close()

    result = check_breaker_veto(_order(ticker="CORZ", side="BUY"), thesis_breaker_state=None, db_path=db_path)

    assert result["passed"] is True


def test_check_breaker_veto_reads_triggered_state_from_sqlite(tmp_path):
    """With no state passed, a TRIGGERED breaker stored in SQLite vetoes the buy."""
    db_path = _db_with_breaker(tmp_path, "TRIGGERED")

    result = check_breaker_veto(_order(ticker="CORZ", side="BUY"), db_path=db_path)

    assert result["passed"] is False and result["breaker"] == "rsi-low"


def test_check_breaker_veto_ok_state_in_sqlite_passes(tmp_path):
    """A breaker stored as OK does not veto."""
    db_path = _db_with_breaker(tmp_path, "OK")
    assert check_breaker_veto(_order(ticker="CORZ", side="BUY"), db_path=db_path)["passed"] is True


def test_a_broken_database_stops_the_gate_instead_of_skipping_the_veto(tmp_path):
    """An unreadable database raises; it never silently lets a buy through."""
    import sqlite3
    import pytest
    bad = tmp_path / "bad.sqlite"
    bad.write_bytes(b"this is not a sqlite database" * 50)
    with pytest.raises(sqlite3.DatabaseError):
        check_breaker_veto(_order(ticker="CORZ", side="BUY"), db_path=bad)


def test_module_has_no_breaker_state_file_path():
    """order_risk_gates has no JSON breaker state path."""
    assert not hasattr(order_risk_gates, "THESIS_BREAKER_STATE_PATH")
    assert "thesis_breaker_state.json" not in Path(order_risk_gates.__file__).read_text()


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
