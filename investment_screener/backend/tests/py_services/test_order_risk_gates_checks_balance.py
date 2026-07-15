"""Tests for order_risk_gates.py — get_available_cash() and
check_available_balance() (Task 5E-5).

check_available_balance() is a BUY-only balance gate: it checks whether
enough cash is available to cover a BUY order's cost, reusing the real,
already-synced portfolio.json broker snapshot (this project's existing
multi-fallback TradingView/Questrade sync pipeline) rather than a new
live Questrade API integration.

get_available_cash() reads that real (but here, always a tmp_path
fixture) portfolio.json — no test in this file ever touches the real,
gitignored portfolio.json. check_available_balance() tests pass
questrade_cash explicitly wherever possible to isolate them from
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
    """shares=10, price=100 -> $1000 cost; questrade_cash=5000 -> passes."""
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, questrade_cash=5000.0)

    assert result["passed"] is True
    assert result["cash_required"] == 1000.0
    assert result["cash_available"] == 5000.0


def test_check_available_balance_fails_with_insufficient_cash():
    """questrade_cash=500 for a $1000 order -> fails."""
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, questrade_cash=500.0)

    assert result["passed"] is False
    assert result["cash_required"] == 1000.0
    assert result["cash_available"] == 500.0


def test_check_available_balance_boundary_exact_cash_passes():
    """questrade_cash exactly equal to cash_required -> passes (< not <=)."""
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, questrade_cash=1000.0)

    assert result["passed"] is True
    assert result["cash_required"] == 1000.0
    assert result["cash_available"] == 1000.0


def test_check_available_balance_sell_orders_never_evaluated():
    """A SELL order is never evaluated -> passed=True, cash_required=0.0."""
    order = _order(side="SELL", shares=10.0, price=100.0)

    result = check_available_balance(order, questrade_cash=0.0)

    assert result["passed"] is True
    assert result["cash_required"] == 0.0


def test_check_available_balance_handles_missing_cash_data(monkeypatch):
    """questrade_cash=None and get_available_cash() (mocked) returns None -> passes, no exception."""
    monkeypatch.setattr(order_risk_gates, "get_available_cash", lambda account=None: None)
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, questrade_cash=None)

    assert result["passed"] is True
    assert result["cash_available"] is None


def test_check_available_balance_fetches_cash_when_not_supplied(monkeypatch):
    """questrade_cash=None -> get_available_cash() called with account forwarded, result used."""
    calls = []

    def fake_get_available_cash(account=None):
        calls.append(account)
        return 5000.0

    monkeypatch.setattr(order_risk_gates, "get_available_cash", fake_get_available_cash)
    order = _order(shares=10.0, price=100.0)

    result = check_available_balance(order, questrade_cash=None, account="TFSA")

    assert calls == ["TFSA"]
    assert result["passed"] is True
    assert result["cash_available"] == 5000.0


# --- get_available_cash() ------------------------------------------------


def test_get_available_cash_reads_portfolio_wide_total(tmp_path, monkeypatch):
    """A real (temp file) portfolio.json fixture with totals.cashUSD; account=None -> correct value."""
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text(json.dumps({"totals": {"cashUSD": 1234.56}}))
    monkeypatch.setattr(order_risk_gates, "PORTFOLIO_PATH", portfolio_file)

    assert get_available_cash() == 1234.56


def test_get_available_cash_reads_specific_account_balance(tmp_path, monkeypatch):
    """Multiple tvSnapshot.snapshots[] entries; account='TFSA' -> that account's cashUSD, not the total."""
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text(json.dumps({
        "totals": {"cashUSD": 9999.0},
        "tvSnapshot": {
            "snapshots": [
                {"accountType": "TFSA", "balances": {"cashUSD": 1000.0}},
                {"accountType": "RRSP", "balances": {"cashUSD": 333.0}},
            ]
        },
    }))
    monkeypatch.setattr(order_risk_gates, "PORTFOLIO_PATH", portfolio_file)

    assert get_available_cash(account="TFSA") == 1000.0
    assert get_available_cash(account="RRSP") == 333.0


def test_get_available_cash_returns_none_for_unknown_account(tmp_path, monkeypatch):
    """account='NONEXISTENT' -> None, no exception."""
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text(json.dumps({
        "tvSnapshot": {"snapshots": [{"accountType": "TFSA", "balances": {"cashUSD": 1000.0}}]},
    }))
    monkeypatch.setattr(order_risk_gates, "PORTFOLIO_PATH", portfolio_file)

    assert get_available_cash(account="NONEXISTENT") is None


def test_get_available_cash_returns_none_when_file_missing(tmp_path, monkeypatch):
    """PORTFOLIO_PATH points at a nonexistent file -> None, no exception."""
    monkeypatch.setattr(order_risk_gates, "PORTFOLIO_PATH", tmp_path / "does_not_exist.json")

    assert get_available_cash() is None


def test_get_available_cash_returns_none_on_malformed_json(tmp_path, monkeypatch):
    """The temp file contains invalid JSON -> None, no exception."""
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text("{not valid json")
    monkeypatch.setattr(order_risk_gates, "PORTFOLIO_PATH", portfolio_file)

    assert get_available_cash() is None
