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
