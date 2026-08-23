"""Tests for order_risk_gates.py — get_available_cash() and
check_available_balance() (Task 5E-5).

check_available_balance() is a BUY-only balance gate: it checks whether
enough cash is available to cover a BUY order's cost, reusing the real,
already-synced portfolio.json broker snapshot (this project's existing
multi-fallback TradingView/broker sync pipeline) rather than a new
live Broker API integration.

get_available_cash() reads that real (but here, always a tmp_path
fixture) portfolio.json — no test in this file ever touches the real,
gitignored portfolio.json. check_available_balance() tests pass
available_cash_override explicitly wherever possible to isolate them from
get_available_cash()'s own file-reading tests.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402
from order_risk_gates import check_available_balance, get_available_cash  # noqa: E402


def _order(side="BUY", ticker="CORZ", shares=10.0, price=100.0):
    return {"ticker": ticker, "side": side, "shares": shares, "price": price}


# --- check_available_balance() ------------------------------------------


def test_check_available_balance_passes_with_sufficient_cash():
    """shares=10, price=100 -> $1000 cost; available_cash_override=5000 -> passes."""
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, available_cash_override=5000.0)

    assert result["passed"] is True
    assert result["cash_required"] == 1000.0
    assert result["cash_available"] == 5000.0


def test_check_available_balance_fails_with_insufficient_cash():
    """available_cash_override=500 for a $1000 order -> fails."""
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, available_cash_override=500.0)

    assert result["passed"] is False
    assert result["cash_required"] == 1000.0
    assert result["cash_available"] == 500.0


def test_check_available_balance_boundary_exact_cash_passes():
    """available_cash_override exactly equal to cash_required -> passes (< not <=)."""
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, available_cash_override=1000.0)

    assert result["passed"] is True
    assert result["cash_required"] == 1000.0
    assert result["cash_available"] == 1000.0


def test_check_available_balance_sell_orders_never_evaluated():
    """A SELL order is never evaluated -> passed=True, cash_required=0.0."""
    order = _order(side="SELL", shares=10.0, price=100.0)

    result = check_available_balance(order, available_cash_override=0.0)

    assert result["passed"] is True
    assert result["cash_required"] == 0.0


def test_check_available_balance_handles_missing_cash_data(monkeypatch):
    """available_cash_override=None and get_available_cash() (mocked) returns None -> passes, no exception."""
    monkeypatch.setattr(order_risk_gates, "get_available_cash", lambda account=None: None)
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, available_cash_override=None)

    assert result["passed"] is True
    assert result["cash_available"] is None


def test_check_available_balance_fetches_cash_when_not_supplied(monkeypatch):
    """available_cash_override=None -> get_available_cash() called with account forwarded, result used."""
    calls = []

    def fake_get_available_cash(account=None):
        calls.append(account)
        return 5000.0

    monkeypatch.setattr(order_risk_gates, "get_available_cash", fake_get_available_cash)
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, available_cash_override=None, account="TFSA")

    assert calls == ["TFSA"]
    assert result["passed"] is True
    assert result["cash_available"] == 5000.0


# --- get_available_cash() (Wave 3: reads domain_model.sqlite CASH_USD rows) ---
#
# The five tests below replace the pre-Wave-3 portfolio.json-fixture tests.
# Cash is a real CASH_USD account_investment row (Wave 0 decision 5), so both
# the portfolio-wide total and per-account cash are derived from SQLite via
# portfolio_repository.get_total_cash_usd/get_account_cash_usd — never from
# portfolio.json's totals.cashUSD / tvSnapshot balances.


def _seed_cash_db(tmp_path, cash_rows):
    """Build a throwaway domain_model.sqlite seeding CASH_USD quantity per
    account (quantity IS the USD dollar amount). Returns the db path."""
    sys.path.insert(0, str(SCRIPT_DIR))
    from domain_model.db_client import initialize_db  # noqa: PLC0415
    from domain_model.account_repository import upsert_account  # noqa: PLC0415
    from domain_model.investment_repository import resolve_investment  # noqa: PLC0415
    from domain_model.investment_price_repository import upsert_investment_price  # noqa: PLC0415
    from domain_model.account_investment_repository import upsert_account_investment  # noqa: PLC0415

    db_path = str(tmp_path / "domain_model.sqlite")
    conn = initialize_db(db_path)
    cash_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
    upsert_investment_price(conn, cash_id, price=1.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    for account_id, amount in cash_rows:
        upsert_account(conn, account_id, account_id, account_id)
        upsert_account_investment(
            conn, account_id, cash_id, quantity=amount, average_cost=1.0,
            book_value=amount, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
    conn.close()
    return db_path


def test_get_available_cash_reads_portfolio_wide_total(tmp_path, monkeypatch):
    """account=None -> SUM of all accounts' CASH_USD quantity."""
    db_path = _seed_cash_db(tmp_path, [("TFSA", 1000.0), ("RRSP", 234.56)])
    monkeypatch.setattr(order_risk_gates, "DB_PATH", db_path)

    assert get_available_cash() == 1234.56


def test_get_available_cash_reads_specific_account_balance(tmp_path, monkeypatch):
    """account='TFSA' -> that account's CASH_USD quantity, not the portfolio total."""
    db_path = _seed_cash_db(tmp_path, [("TFSA", 1000.0), ("RRSP", 333.0)])
    monkeypatch.setattr(order_risk_gates, "DB_PATH", db_path)

    assert get_available_cash(account="TFSA") == 1000.0
    assert get_available_cash(account="RRSP") == 333.0


def test_get_available_cash_returns_none_for_unknown_account(tmp_path, monkeypatch):
    """account='NONEXISTENT' -> None, no exception."""
    db_path = _seed_cash_db(tmp_path, [("TFSA", 1000.0)])
    monkeypatch.setattr(order_risk_gates, "DB_PATH", db_path)

    assert get_available_cash(account="NONEXISTENT") is None


def test_get_available_cash_returns_none_when_no_cash_rows(tmp_path, monkeypatch):
    """An empty DB (no CASH_USD rows) -> None, no exception."""
    db_path = _seed_cash_db(tmp_path, [])
    monkeypatch.setattr(order_risk_gates, "DB_PATH", db_path)

    assert get_available_cash() is None


def test_get_available_cash_never_raises_on_bad_db_path(tmp_path, monkeypatch):
    """A nonexistent/invalid DB path degrades to None (or an empty total), never raises."""
    monkeypatch.setattr(order_risk_gates, "DB_PATH", str(tmp_path / "does_not_exist.sqlite"))

    assert get_available_cash() is None
