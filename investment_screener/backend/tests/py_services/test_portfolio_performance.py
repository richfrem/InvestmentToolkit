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

from portfolio_performance import compute_performance, load_portfolio_data, unpriced_holdings  # noqa: E402
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


class TestCurrentTotalOverride:
    """Hybrid data-source design: yfinance daily closes lag intraday, so a
    yfinance-only 'current' value can equal yesterday's close, producing a
    false 0% 1-day change. TradingView's broker_reported_total is refreshed
    live on every sync — use it for 'currentValue' when available, while
    still reconstructing the PAST total from yfinance history (TradingView
    has no historical equity API)."""

    def test_current_total_override_replaces_the_yfinance_reconstructed_current_value(self):
        close = _build_close_df()
        shares_map = {"AAPL": 10, "PSU-U.TO": 80}
        tickers = ["AAPL", "PSU-U.TO"]
        now = datetime(2026, 7, 2, 12, 0, 0)

        result = compute_performance(
            close, shares_map, cash_value=0.0, tickers=tickers, now=now,
            current_total_override=99999.0,
        )

        assert result["1d"]["currentValue"] == 99999.0
        expected_past_total = 10 * 202.0 + 80 * 100.05
        assert abs(result["1d"]["change"] - (99999.0 - expected_past_total)) < 0.01
        expected_pct = (99999.0 - expected_past_total) / expected_past_total * 100
        assert abs(result["1d"]["changePct"] - expected_pct) < 0.01

    def test_no_override_preserves_existing_yfinance_reconstruction_behavior(self):
        close = _build_close_df()
        shares_map = {"AAPL": 10, "PSU-U.TO": 80}
        tickers = ["AAPL", "PSU-U.TO"]
        now = datetime(2026, 7, 2, 12, 0, 0)

        result = compute_performance(close, shares_map, cash_value=0.0, tickers=tickers, now=now)

        expected_current = 10 * 204.0 + 80 * 100.09
        assert abs(result["1d"]["currentValue"] - expected_current) < 0.01


class TestSharedPeriodDefinition:
    """Portfolio-level 1D/1W/1M/3M use the same reference dates as every per-stock
    % change (price_changes.period_reference_dates, AGENTS.md rule 22). Before
    2026-09-28 this file had its own rules (1M = 30 days) and only 35 days of history."""

    def _daily_close(self, start, end, price_for):
        idx = pd.bdate_range(start, end)
        return pd.DataFrame({"AAA": [price_for(d) for d in idx]}, index=idx)

    def test_periods_follow_the_shared_reference_dates(self):
        from price_changes import period_reference_dates
        now = datetime(2026, 3, 31, 12, 0, 0)
        close = self._daily_close("2025-11-01", "2026-03-31", lambda d: float(d.toordinal() % 40 + 60))
        result = compute_performance(close, {"AAA": 1}, cash_value=0.0, tickers=["AAA"], now=now)
        refs = period_reference_dates(now.date())
        assert set(result) == {"1d", "1w", "1m", "3m"}
        for p in ("1d", "1w", "1m", "3m"):
            past = close.loc[close.index <= pd.Timestamp(refs[p]), "AAA"].iloc[-1]
            assert result[p]["historicalValue"] == round(past, 2)

    def test_one_month_is_a_calendar_month_not_thirty_days(self):
        now = datetime(2026, 3, 31, 12, 0, 0)
        # 30 days back is 03-01 (Sun) -> 02-27; a calendar month back is 02-28 (Sat) -> 02-27 too,
        # so pick a date where they differ: 2026-05-31 -> 30d = 05-01 (Fri), 1 month = 04-30 (Thu).
        now = datetime(2026, 5, 31, 12, 0, 0)
        close = self._daily_close("2026-04-01", "2026-05-29",
                                  lambda d: 50.0 if d.date().isoformat() == "2026-04-30" else 100.0)
        result = compute_performance(close, {"AAA": 1}, cash_value=0.0, tickers=["AAA"], now=now)
        assert result["1m"]["historicalValue"] == 50.0


class TestHoldingsWithoutPriceHistory:
    """A holding with no price at a past date must not count as $0 then and full value
    now. On 2026-10-08 the $3,590 cash row (CASH_USD) did exactly that and every period
    read about +9%."""

    def test_synced_cash_is_cash_not_an_equity(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        upsert_account(conn, "TFSA", "TFSA", "TFSA")
        cash_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
        upsert_account_investment(conn, "TFSA", cash_id, quantity=3590.59, average_cost=1.0,
                                  book_value=3590.59, currency="USD", last_synced_at="2026-10-08T00:00:00Z")
        conn.close()
        cash_value, tickers, shares_map = load_portfolio_data("unused", db_path=db_path)
        assert (round(cash_value, 2), tickers, shares_map) == (3590.59, [], {})

    def test_a_holding_with_no_history_is_held_flat_at_its_stored_price(self):
        dates = pd.to_datetime(["2026-10-06", "2026-10-07", "2026-10-08"])
        close = pd.DataFrame({"AAPL": [200.0, 202.0, 204.0], "NOHIST": [float("nan")] * 3}, index=dates)
        result = compute_performance(close, {"AAPL": 10, "NOHIST": 100}, 0.0, ["AAPL", "NOHIST"],
                                     datetime(2026, 10, 8, 12), fallback_prices={"NOHIST": 30.0})
        assert result["1d"]["historicalValue"] == 10 * 202.0 + 100 * 30.0
        assert result["1d"]["change"] == 20.0   # only AAPL moved
        assert unpriced_holdings(close, ["AAPL", "NOHIST", "ABSENT"]) == ["NOHIST", "ABSENT"]

    def test_a_holding_listed_after_the_reference_date_is_held_flat_before_it_traded(self):
        dates = pd.to_datetime(["2026-09-01", "2026-10-07", "2026-10-08"])
        close = pd.DataFrame({"AAPL": [190.0, 202.0, 204.0], "NEWCO": [float("nan"), 50.0, 55.0]}, index=dates)
        result = compute_performance(close, {"AAPL": 10, "NEWCO": 10}, 0.0, ["AAPL", "NEWCO"], datetime(2026, 10, 8, 12))
        assert result["1m"]["historicalValue"] == 10 * 190.0 + 10 * 50.0   # first traded price, not $0
        assert unpriced_holdings(close, ["AAPL", "NEWCO"]) == []
