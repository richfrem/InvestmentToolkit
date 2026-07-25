#!/usr/bin/env python3
"""
test_watchlist_manager.py — Unit tests for the new watchlist manager script.
No production code is written before a failing test exists (TDD Iron Law).
"""

import sys
import unittest
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WATCHLIST_SCRIPT = REPO_ROOT / "plugins/tradingview/scripts/watchlist_manager.py"

sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402
import watchlist_manager  # noqa: E402

class TestWatchlistManager(unittest.TestCase):
    def test_script_exists_and_runs_help(self):
        """Verify the manager script exists and handles help flags."""
        self.assertTrue(WATCHLIST_SCRIPT.exists(), "watchlist_manager.py script must exist")
        r = subprocess.run(
            ["python3", str(WATCHLIST_SCRIPT), "--help"],
            capture_output=True, text=True, timeout=5
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("watchlist", r.stdout.lower() or r.stderr.lower())

    def test_sync_dry_run(self):
        """Verify the dry run option outputs a planned list of changes."""
        r = subprocess.run(
            ["python3", str(WATCHLIST_SCRIPT), "sync", "--dry-run"],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout.strip())
        self.assertIn("success", data)
        self.assertIn("actions", data)
        # BOATS session removed (TradingView charts now natively support 24h
        # quoting) — only the two real, renamed TradingView lists remain.
        self.assertEqual(set(data["actions"].keys()), {"TV-Full Watchlist", "TV-Portfolio"})

class TestLoadResearchedWatchlistDbFallback(unittest.TestCase):
    """Wave 1 Task 7B — fallback (no watchlist.json) enumerates tickers with a
    projection row in domain_model.sqlite, not projections/*.json filenames."""

    def test_fallback_lists_symbols_with_projections(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            conn = initialize_db(str(db_path))
            try:
                for ticker in ("NVDA", "AMD"):
                    investment_id = resolve_investment(conn, ticker, asset_class="EQUITY")
                    save_projection_version(
                        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
                        fair_value=100.0, action="HOLD", source="AI_AGENT",
                    )
            finally:
                conn.close()

            original_target_path = watchlist_manager.TARGET_WATCHLIST_PATH
            watchlist_manager.TARGET_WATCHLIST_PATH = Path(tmp) / "does_not_exist.json"
            try:
                tickers = watchlist_manager.load_researched_watchlist(db_path=db_path)
            finally:
                watchlist_manager.TARGET_WATCHLIST_PATH = original_target_path

            self.assertEqual(tickers, ["AMD", "NVDA"])

    def test_fallback_returns_empty_for_no_projections(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            initialize_db(str(db_path)).close()

            original_target_path = watchlist_manager.TARGET_WATCHLIST_PATH
            watchlist_manager.TARGET_WATCHLIST_PATH = Path(tmp) / "does_not_exist.json"
            try:
                tickers = watchlist_manager.load_researched_watchlist(db_path=db_path)
            finally:
                watchlist_manager.TARGET_WATCHLIST_PATH = original_target_path

            self.assertEqual(tickers, [])


class TestLoadWatchlistedSymbols(unittest.TestCase):
    """Wave 2 Task 10 — watchlist membership reads investment.is_watchlisted
    via list_investments(), not watchlist.json."""

    def test_reads_watchlisted_symbols_from_sqlite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            conn = initialize_db(str(db_path))
            try:
                for ticker in ("MSFT", "TSLA"):
                    investment_id = resolve_investment(conn, ticker, asset_class="EQUITY")
                    update_investment_fields(conn, investment_id, is_watchlisted=True)
                # Not watchlisted — must be excluded.
                resolve_investment(conn, "AAPL", asset_class="EQUITY")
            finally:
                conn.close()

            tickers = watchlist_manager.load_researched_watchlist(db_path=db_path)
            self.assertEqual(tickers, ["MSFT", "TSLA"])


class TestLoadHoldingsFromSqlite(unittest.TestCase):
    """Wave 3 Task 6 — held positions come from account_investment in
    domain_model.sqlite, not portfolio.json."""

    def _seed_holding(self, conn, ticker):
        from domain_model.account_repository import upsert_account
        from domain_model.investment_price_repository import upsert_investment_price
        from domain_model.account_investment_repository import upsert_account_investment

        upsert_account(conn, "TFSA", "TFSA", "TFSA")
        investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, investment_id, price=100.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", investment_id, quantity=1, average_cost=100.0,
            book_value=100.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )

    def test_load_holdings_watchlist_reads_sqlite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            conn = initialize_db(str(db_path))
            try:
                self._seed_holding(conn, "AAPL")
            finally:
                conn.close()

            tickers = watchlist_manager.load_holdings_watchlist(db_path=db_path)
            self.assertEqual(tickers, ["AAPL"])

    def test_load_holdings_watchlist_excludes_cash_usd(self):
        """The real cash symbol domain_model.sqlite stores is CASH_USD (see
        `investment.asset_class='CASH'`), not USD_CASH. TradingView has no
        symbol for cash — it must never be pushed into a TV watchlist, even
        though it's a real, useful row to keep in the domain model itself."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            conn = initialize_db(str(db_path))
            try:
                self._seed_holding(conn, "AAPL")
                self._seed_holding(conn, "CASH_USD")
            finally:
                conn.close()

            tickers = watchlist_manager.load_holdings_watchlist(db_path=db_path)
            self.assertEqual(tickers, ["AAPL"])

    def test_missing_db_returns_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            missing_db = Path(tmp) / "missing.sqlite"
            tickers = watchlist_manager.load_holdings_watchlist(db_path=missing_db)
            self.assertEqual(tickers, [])


if __name__ == "__main__":
    unittest.main()
