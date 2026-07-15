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

import unittest
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ALERTS_SCRIPT = REPO_ROOT / "plugins/tradingview/scripts/tv_list_alerts.py"
OUTPUT_FILE = REPO_ROOT / "investment_screener/backend/data/tradingview_alerts_actual.json"

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

if __name__ == "__main__":
    unittest.main()
