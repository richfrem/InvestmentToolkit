"""
Tests portfolio_performance.py's handling of missing/NaN prices in the historical
close DataFrame — e.g. PSU-U.TO (TSX) has no trading data on Canadian market
holidays like Canada Day (2026-07-01), while US tickers trade normally.

Bug (2026-07-02): safe_float(NaN) -> 0.0 meant a holiday gap for one position
zeroed out that position's contribution to the historical total, producing an
impossible +29.79% 1-day return. Missing prices must be forward-filled (last
known price) before computing equity value, not treated as worthless.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from portfolio_performance import compute_performance, load_portfolio_data  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402


class TestLoadPortfolioDataReadsSqlite:
    """Wave 3 Task 6: load_portfolio_data() must read domain_model.sqlite,
    never portfolio.json (the portfolio_path arg is retained for call-site
    signature compatibility only, mirroring portfolio_io.py's own pattern)."""

    def test_splits_cash_and_equity_from_sqlite(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        upsert_account(conn, "TFSA", "TFSA", "TFSA")
        aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
        cash_id = resolve_investment(conn, "USD_CASH", asset_class="CASH", currency="USD")
        upsert_investment_price(conn, aapl_id, price=200.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_investment_price(conn, cash_id, price=1.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", aapl_id, quantity=10, average_cost=180.0,
            book_value=1800.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        upsert_account_investment(
            conn, "TFSA", cash_id, quantity=500.0, average_cost=1.0,
            book_value=500.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        conn.close()

        cash_value, tickers, shares_map = load_portfolio_data("unused-path.json", db_path=db_path)

        assert cash_value == 500.0
        assert tickers == ["AAPL"]
        assert shares_map == {"AAPL": 10}

    def test_missing_db_returns_empty(self, tmp_path):
        cash_value, tickers, shares_map = load_portfolio_data(
            "unused-path.json", db_path=tmp_path / "missing.sqlite"
        )
        assert cash_value == 0.0
        assert tickers == []
        assert shares_map == {}


def _build_close_df():
    """Mirrors the real PSU-U.TO Canada Day gap: one ticker (PSU-U.TO) has a NaN
    on the middle date while another ticker (AAPL) trades normally every day."""
    dates = pd.to_datetime(["2026-06-30", "2026-07-01", "2026-07-02"])
    return pd.DataFrame(
        {
            "AAPL": [200.0, 202.0, 204.0],
            "PSU-U.TO": [100.05, float("nan"), 100.09],
        },
        index=dates,
    )


def test_forward_fills_nan_price_instead_of_treating_it_as_zero():
    close = _build_close_df()
    shares_map = {"AAPL": 10, "PSU-U.TO": 80}
    tickers = ["AAPL", "PSU-U.TO"]
    now = datetime(2026, 7, 2, 12, 0, 0)

    result = compute_performance(close, shares_map, cash_value=0.0, tickers=tickers, now=now)

    # "1d" looks back to 2026-07-01, where PSU-U.TO is NaN. Forward-filled value
    # should be 100.05 (last known, from 06-30), NOT 0.0.
    expected_past_total = 10 * 202.0 + 80 * 100.05
    assert abs(result["1d"]["historicalValue"] - expected_past_total) < 0.01


def test_a_holiday_gap_does_not_produce_an_inflated_return():
    close = _build_close_df()
    shares_map = {"AAPL": 10, "PSU-U.TO": 80}
    tickers = ["AAPL", "PSU-U.TO"]
    now = datetime(2026, 7, 2, 12, 0, 0)

    result = compute_performance(close, shares_map, cash_value=0.0, tickers=tickers, now=now)

    # With the bug, PSU-U.TO's ~$8007 contribution vanishes from historicalValue,
    # producing a >20% swing from a position that barely moved. Real day-over-day
    # move here (AAPL 202->204, PSU-U.TO 100.05->100.09) should be a small single-digit
    # percent change, not >20%.
    assert abs(result["1d"]["changePct"]) < 5.0


def test_current_value_uses_the_latest_row_even_with_a_prior_gap():
    close = _build_close_df()
    shares_map = {"AAPL": 10, "PSU-U.TO": 80}
    tickers = ["AAPL", "PSU-U.TO"]
    now = datetime(2026, 7, 2, 12, 0, 0)

    result = compute_performance(close, shares_map, cash_value=0.0, tickers=tickers, now=now)

    expected_current = 10 * 204.0 + 80 * 100.09
    assert abs(result["1d"]["currentValue"] - expected_current) < 0.01
