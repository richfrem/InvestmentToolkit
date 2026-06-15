"""Tests for overnight_gaps.py — extended-hours gap scanner.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import overnight_gaps  # noqa: E402


class TestImport:
    def test_module_imports(self):
        assert hasattr(overnight_gaps, "get_overnight_gaps")
        assert hasattr(overnight_gaps, "_load_tickers")
        assert hasattr(overnight_gaps, "_fetch_gap")
        assert hasattr(overnight_gaps, "_is_scannable")


class TestIsScannable:
    def test_us_equity_passes(self):
        assert overnight_gaps._is_scannable("NVDA") is True

    def test_canadian_to_blocked(self):
        assert overnight_gaps._is_scannable("SHOP.TO") is False

    def test_futures_blocked(self):
        assert overnight_gaps._is_scannable("NQ1!") is False

    def test_lowercase_us_passes(self):
        assert overnight_gaps._is_scannable("aapl") is True
