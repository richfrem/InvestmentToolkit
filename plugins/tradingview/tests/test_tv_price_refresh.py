#!/usr/bin/env python3
"""
test_tv_price_refresh.py - Tests for the SQLite-backed price refresh.

Purpose:
    The daily loop needs current `investment_price` rows before the brief is
    built. Verifies the refresh covers held and watchlisted symbols, writes
    through the repository, keeps (and reports) the old row when a quote is
    missing, and never fabricates a price.

Layer:
    Testing / Plugins / TradingView

Usage Examples:
    pytest plugins/tradingview/tests/test_tv_price_refresh.py

Key Functions (Index):
    - test_scope_is_held_plus_watchlisted_and_skips_closed_and_cash()
    - test_prices_and_sector_are_written_with_the_run_timestamp()
    - test_a_missing_quote_keeps_the_old_row_and_is_reported()
    - test_aliases_are_normalised_before_fetching_and_writing()

Key Input Dependencies:
    - plugins/tradingview/scripts/tv_price_refresh.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))

from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_price_repository import get_investment_price, upsert_investment_price  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from tv_price_refresh import refresh_prices, refresh_scope  # noqa: E402

NOW = "2026-10-09T16:00:00+00:00"
OLD = "2026-10-08T15:05:41.725Z"


def _db(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model.sqlite"))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    return conn


def _hold(conn, account, symbol, quantity):
    investment_id = resolve_investment(conn, symbol)
    upsert_account_investment(conn, account, investment_id, quantity, 10.0, 10.0 * quantity, "USD", OLD)
    return investment_id


def _quotes(prices, sector="Technology", industry="Semiconductors"):
    def fetch(items):
        return {"stocks": [{"symbol": i["symbol"], "price": prices[i["symbol"]], "sector": sector, "industry": industry}
                           for i in items if i["symbol"] in prices]}
    return fetch


def test_scope_is_held_plus_watchlisted_and_skips_closed_and_cash(tmp_path):
    conn = _db(tmp_path)
    _hold(conn, "TFSA", "BE", 4)
    _hold(conn, "RRSP", "BE", 2)
    _hold(conn, "TFSA", "OLD", 0)
    _hold(conn, "TFSA", "CASH_USD", 126.32)
    watch = resolve_investment(conn, "ASTS")
    update_investment_fields(conn, watch, is_watchlisted=1)
    assert refresh_scope(conn) == ["ASTS", "BE"]


def test_prices_and_sector_are_written_with_the_run_timestamp(tmp_path):
    conn = _db(tmp_path)
    be = _hold(conn, "TFSA", "BE", 4)
    result = refresh_prices(conn, fetch=_quotes({"BE": 274.07}), now=NOW)
    row = get_investment_price(conn, be)
    assert (row["price"], row["currency"], row["fetched_at"]) == (274.07, "USD", NOW)
    sector = conn.execute("SELECT sector, industry FROM investment WHERE investment_id = ?", (be,)).fetchone()
    assert tuple(sector) == ("Technology", "Semiconductors")
    assert result == {"written": ["BE"], "failed": [], "stale": []}


def test_a_missing_quote_keeps_the_old_row_and_is_reported(tmp_path):
    conn = _db(tmp_path)
    be = _hold(conn, "TFSA", "BE", 4)
    mu = _hold(conn, "TFSA", "MU", 1)
    upsert_investment_price(conn, mu, 900.0, "USD", OLD)
    result = refresh_prices(conn, fetch=_quotes({"BE": 274.07, "MU": 0}), now=NOW)
    assert get_investment_price(conn, mu)["price"] == 900.0
    assert get_investment_price(conn, mu)["fetched_at"] == OLD
    assert result["written"] == ["BE"]
    assert result["failed"] == ["MU"]
    assert result["stale"] == [{"symbol": "MU", "fetched_at": OLD}]


def test_aliases_are_normalised_before_fetching_and_writing(tmp_path):
    conn = _db(tmp_path)
    _hold(conn, "TFSA", "PSU.U.TO", 90)
    seen = []

    def fetch(items):
        seen.extend(i["symbol"] for i in items)
        return {"stocks": [{"symbol": "PSU-U.TO", "price": 99.5, "sector": "Financial Services", "industry": "Asset Management"}]}

    result = refresh_prices(conn, fetch=fetch, now=NOW)
    assert seen == ["PSU-U.TO"]
    assert result["written"] == ["PSU-U.TO"]
    assert get_investment_price(conn, "PSU-U.TO")["price"] == 99.5
