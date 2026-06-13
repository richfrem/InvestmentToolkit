#!/usr/bin/env python3
"""
test_watchlist_manager.py — Unit tests for the new watchlist manager script.
No production code is written before a failing test exists (TDD Iron Law).
"""

import unittest
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WATCHLIST_SCRIPT = REPO_ROOT / "plugins/tradingview/scripts/watchlist_manager.py"

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

if __name__ == "__main__":
    unittest.main()
