"""
Tests fetch_broker_data.py's Wave 3 Task 8 balances-only exchange-rate refresh.

Context: a price-only refresh (routes/portfolio.ts POST /refresh-prices) never
triggers a full broker sync, so the stored USD->CAD rate could go stale relative
to freshly-refreshed USD prices. refresh_exchange_rate_only() does a LIGHTWEIGHT
balance-only fetch (--balances, no full position sync) and persists the rate
computed from it, so a price refresh can keep the rate fresh too without paying
for a full --snapshot sync.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "plugins/tradingview/scripts"
DOMAIN_MODEL_PY_SERVICES_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(DOMAIN_MODEL_PY_SERVICES_DIR))

import fetch_broker_data  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.exchange_rate_repository import get_exchange_rate  # noqa: E402


def test_refresh_exchange_rate_only_computes_and_stores_rate(tmp_path, monkeypatch):
    """Balances-only payload with a known CAD/USD ratio must produce that exact rate."""
    db_path = str(tmp_path / "test.sqlite")
    balances = {
        "totalEquityCADCombined": 8280.0,
        "totalEquityUSDCombined": 6000.0,
    }
    monkeypatch.setattr(fetch_broker_data, "fetch_tv_balances", lambda: balances)

    rate = fetch_broker_data.refresh_exchange_rate_only(db_path=db_path)

    assert rate == 1.38
    conn = initialize_db(db_path)
    assert get_exchange_rate(conn) == 1.38


def test_refresh_exchange_rate_only_returns_none_on_balance_error(tmp_path, monkeypatch):
    """A failed balances fetch must not write a bogus rate."""
    db_path = str(tmp_path / "test.sqlite")
    monkeypatch.setattr(fetch_broker_data, "fetch_tv_balances", lambda: {"error": "CDP unreachable"})

    rate = fetch_broker_data.refresh_exchange_rate_only(db_path=db_path)

    assert rate is None
    conn = initialize_db(db_path)
    assert get_exchange_rate(conn) is None


def test_refresh_exchange_rate_only_falls_back_to_non_combined_fields(tmp_path, monkeypatch):
    """Balances payload may report totalEquityCAD/USD instead of the *Combined variants."""
    db_path = str(tmp_path / "test.sqlite")
    balances = {"totalEquityCAD": 1380.0, "totalEquityUSD": 1000.0}
    monkeypatch.setattr(fetch_broker_data, "fetch_tv_balances", lambda: balances)

    rate = fetch_broker_data.refresh_exchange_rate_only(db_path=db_path)

    assert rate == 1.38
    conn = initialize_db(db_path)
    assert get_exchange_rate(conn) == 1.38


def test_refresh_exchange_rate_only_returns_none_on_zero_usd(tmp_path, monkeypatch):
    """A zero/missing USD total must not divide-by-zero or write a bogus rate."""
    db_path = str(tmp_path / "test.sqlite")
    balances = {"totalEquityCADCombined": 0.0, "totalEquityUSDCombined": 0.0}
    monkeypatch.setattr(fetch_broker_data, "fetch_tv_balances", lambda: balances)

    rate = fetch_broker_data.refresh_exchange_rate_only(db_path=db_path)

    assert rate is None
    conn = initialize_db(db_path)
    assert get_exchange_rate(conn) is None
