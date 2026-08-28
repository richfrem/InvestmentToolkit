"""Tests for earnings_calendar.py — ETF classification.

ETFs (DRAM, HUMN, KOID, etc.) have no earnings dates. They must be excluded
from earnings lookups entirely — not reported as UNKNOWN "blind spots" and
not hammered with yfinance 404s every brief run.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_earnings_calendar.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import earnings_calendar  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402


def _make_db_with_holdings(tmp_path, tickers):
    """Seed domain_model.sqlite with held positions — Wave 3 Task 6 cutover of
    _load_tickers() off portfolio.json onto SQLite."""
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    for t in tickers:
        investment_id = resolve_investment(conn, t, asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, investment_id, price=100.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", investment_id, quantity=1, average_cost=100.0,
            book_value=100.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
    conn.close()
    return db_path


class TestEtfClassification:
    """Known ETFs in the portfolio must never hit the earnings lookup path."""

    def test_known_etfs_declared(self):
        """DRAM (HBM/memory), HUMN (humanoid robotics), KOID (robotics) are ETFs."""
        for etf in ("DRAM", "HUMN", "KOID"):
            assert etf in earnings_calendar.ETF_TICKERS, (
                f"{etf} is an ETF — must be in ETF_TICKERS so it is excluded "
                f"from earnings lookups instead of reported as a blind spot"
            )

    def test_load_tickers_excludes_etfs(self, tmp_path: Path):
        """Portfolio with AAPL + 3 ETFs → only AAPL gets an earnings lookup."""
        db_path = _make_db_with_holdings(tmp_path, ["AAPL", "DRAM", "HUMN", "KOID"])
        assert earnings_calendar._load_tickers(db_path) == ["AAPL"]

    def test_cash_skip_list_still_applies(self, tmp_path: Path):
        db_path = _make_db_with_holdings(tmp_path, ["PSU-U.TO", "MSFT"])
        assert earnings_calendar._load_tickers(db_path) == ["MSFT"]

    def test_missing_db_returns_empty(self, tmp_path: Path):
        missing_db = tmp_path / "missing.sqlite"
        assert earnings_calendar._load_tickers(missing_db) == []


class TestCashUsdSkipList:
    """Caught live 2026-08-28: technicals.py's _default_earnings_anchor() calling
    get_earnings_calendar() surfaced a 404 for symbol CASH_USD — the synthetic
    cash row used everywhere else in this codebase. SKIP_TICKERS only listed
    'USD_CASH' (reversed spelling), a stale/wrong alias that let the real
    CASH_USD symbol slip through and hit yfinance."""

    def test_cash_usd_alias_is_skipped(self, tmp_path: Path):
        db_path = _make_db_with_holdings(tmp_path, ["CASH_USD", "MSFT"])
        assert earnings_calendar._load_tickers(db_path) == ["MSFT"]


class TestTickerFilter:
    """Caught live 2026-08-28: technicals.py needs one ticker's earnings date for
    its anchored-VWAP auto-anchor, but get_earnings_calendar() had no filter —
    every single-ticker technicals.py run silently fetched the ENTIRE portfolio's
    earnings dates (including synthetic/ETF/delisted symbols), producing stray
    yfinance 404 noise unrelated to the ticker actually being analyzed."""

    def test_ticker_filter_only_fetches_requested_tickers(self, monkeypatch):
        fetched = []

        def _fake_fetch(ticker):
            fetched.append(ticker)
            return None, None

        monkeypatch.setattr(earnings_calendar, "_load_tickers", lambda: ["AAPL", "MSFT", "GOOG"])
        monkeypatch.setattr(earnings_calendar, "_fetch_earnings_date", _fake_fetch)

        earnings_calendar.get_earnings_calendar(tickers=["AAPL"])

        assert fetched == ["AAPL"], (
            f"Expected only the filtered ticker to be fetched, got {fetched}"
        )

    def test_no_filter_still_fetches_full_portfolio(self, monkeypatch):
        """Default (no filter) behavior — used by the daily brief — must be unchanged."""
        fetched = []

        def _fake_fetch(ticker):
            fetched.append(ticker)
            return None, None

        monkeypatch.setattr(earnings_calendar, "_load_tickers", lambda: ["AAPL", "MSFT", "GOOG"])
        monkeypatch.setattr(earnings_calendar, "_fetch_earnings_date", _fake_fetch)

        earnings_calendar.get_earnings_calendar()

        assert fetched == ["AAPL", "MSFT", "GOOG"]
