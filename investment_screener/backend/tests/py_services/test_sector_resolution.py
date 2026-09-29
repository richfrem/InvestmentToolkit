"""
test_sector_resolution.py — sector/industry precedence for heatmap rows (which the
refresh then persists into investment.sector, so every page inherits it).

Before 2026-09-28 the caller's stored sector won over SECTOR_OVERRIDES, so a bad
value persisted from yfinance (AMAT and FOTO stored as the literal "Unknown")
could never be corrected by the override list.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from fetch_portfolio_heatmap import resolve_sector  # noqa: E402
from sector_overrides import SECTOR_OVERRIDES  # noqa: E402

YAHOO = {"sector": "Technology", "industry": "Semiconductors"}


def test_override_beats_stored_and_yahoo_values():
    SECTOR_OVERRIDES["ZZTEST"] = {"sector": "Technology", "industry": "ETF - Photonics"}
    try:
        assert resolve_sector("ZZTEST", "ZZTEST", "Unknown", "Unknown", YAHOO) == ("Technology", "ETF - Photonics")
        assert resolve_sector("ZZTEST", "ZZTEST", "Financial Services", "Capital Markets", YAHOO) == ("Technology", "ETF - Photonics")
    finally:
        del SECTOR_OVERRIDES["ZZTEST"]


def test_stored_unknown_falls_through_to_yahoo():
    assert resolve_sector("AAAA", "AAAA", "Unknown", "Unknown", YAHOO) == ("Technology", "Semiconductors")


def test_stored_value_kept_when_real_and_not_overridden():
    assert resolve_sector("AAAA", "AAAA", "Industrials", "Electrical Equipment & Parts", YAHOO) == (
        "Industrials", "Electrical Equipment & Parts")


def test_nothing_known_is_unknown():
    assert resolve_sector("AAAA", "AAAA", None, None, {}) == ("Unknown", "Unknown")


def test_normalized_symbol_override_applies():
    SECTOR_OVERRIDES["ZZTEST.TO"] = {"sector": "CASH", "industry": "CASH"}
    try:
        assert resolve_sector("ZZTEST-TO", "ZZTEST.TO", None, None, YAHOO) == ("CASH", "CASH")
    finally:
        del SECTOR_OVERRIDES["ZZTEST.TO"]
