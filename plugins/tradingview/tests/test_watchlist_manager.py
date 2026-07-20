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
from domain_model.investment_repository import resolve_investment  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
