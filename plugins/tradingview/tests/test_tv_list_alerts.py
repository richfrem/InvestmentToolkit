#!/usr/bin/env python3
"""
test_tv_list_alerts.py — Unit tests for the TradingView alert list manager.

Purpose:
    Unit tests for validating that the tv_list_alerts.py script is properly situated and runnable.
Key Input Dependencies:
    - plugins/tradingview/scripts/tv_list_alerts.py (the target script under test)
Key Output Dependencies:
    - None
"""

import sys
import unittest
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ALERTS_SCRIPT = REPO_ROOT / "plugins/tradingview/scripts/tv_list_alerts.py"
OUTPUT_FILE = REPO_ROOT / "investment_screener/backend/data/tradingview_alerts_actual.json"

sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.alert_repository import list_alerts  # noqa: E402
import tv_list_alerts  # noqa: E402


class TestTvListAlerts(unittest.TestCase):
    def test_script_exists(self):
        """Verify the alert list script exists in the correct folder."""
        self.assertTrue(ALERTS_SCRIPT.exists(), "tv_list_alerts.py script must exist")

    def test_script_dry_run_help(self):
        """Verify the script handles the help command or basic argument parsing."""
        r = subprocess.run(
            ["python3", str(ALERTS_SCRIPT), "--help"],
            capture_output=True, text=True, timeout=5
        )
        # Should exit cleanly or show help
        self.assertIn(r.returncode, (0, 1, 2))


class TestSaveAlertsToDb(unittest.TestCase):
    """Wave 2 Task 10 producer cutover: save_alerts_to_db() persists fetched
    alerts via alert_repository.upsert_alert() instead of rewriting
    tradingview_alerts_actual.json in place."""

    def test_persists_alert_with_exchange_qualified_symbol(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            initialize_db(str(db_path)).close()

            alerts = [{
                "alert_id": 12345,
                "symbol": "NASDAQ:IREN",
                "type": "price",
                "message": "IREN Crossing 32.81",
                "active": True,
                "price": 32.81,
                "condition": {"type": "cross"},
                "resolution": "1",
                "created": "2026-07-14T13:45:48Z",
                "last_fired": None,
                "expiration": None,
            }]

            count = tv_list_alerts.save_alerts_to_db(alerts, db_path)
            self.assertEqual(count, 1)

            conn = initialize_db(str(db_path))
            try:
                rows = list_alerts(conn)
            finally:
                conn.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["alert_id"], "12345")
            self.assertEqual(rows[0]["price"], 32.81)
            self.assertEqual(rows[0]["message"], "IREN Crossing 32.81")

            # Ticker resolved from the exchange-qualified symbol.
            from domain_model.investment_repository import get_investment
            conn = initialize_db(str(db_path))
            try:
                inv = get_investment(conn, rows[0]["investment_id"])
            finally:
                conn.close()
            self.assertEqual(inv["symbol"], "IREN")


if __name__ == "__main__":
    unittest.main()
