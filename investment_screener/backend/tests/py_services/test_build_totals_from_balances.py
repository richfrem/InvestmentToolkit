"""
Tests fetch_broker_data.py::build_totals_from_balances().

Split-brain audit (2026-07-02) found the TS-side buildPortfolioSnapshot() marks
totals as 'tv_authoritative' vs 'computed_fallback' (see portfolioSnapshot.ts +
preserveAuthoritativeTotal()), but the Python-side write_snapshot() never set
totalSource at all when it successfully wrote real TV balance data — meaning a
subsequent TS-side write couldn't recognize Python's authoritative totals as
authoritative, and could have silently overwritten them. This must be fixed for
preserveAuthoritativeTotal() to actually protect Python-sourced totals.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "plugins/tradingview/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from fetch_broker_data import build_totals_from_balances  # noqa: E402


def test_marks_total_source_as_tv_authoritative_on_success():
    balances = {
        "cashUSDCombined": 1130.24,
        "totalEquityUSDCombined": 32903.75,
        "marketValueUSDCombined": 31773.51,
    }
    result = build_totals_from_balances(balances, stored_exchange_rate=1.4214)
    assert result["totalSource"] == "tv_authoritative"


def test_computes_totals_from_combined_balance_fields():
    balances = {
        "cashUSDCombined": 1130.24,
        "totalEquityUSDCombined": 32903.75,
        "marketValueUSDCombined": 31773.51,
    }
    result = build_totals_from_balances(balances, stored_exchange_rate=1.4214)
    assert result["cashUSD"] == 1130.24
    assert result["totalUSD"] == 32903.75
    assert result["holdingsUSD"] == 31773.51
    assert abs(result["totalCAD"] - (32903.75 * 1.4214)) < 0.01


def test_falls_back_to_non_combined_fields_when_combined_missing():
    balances = {
        "cashUSD": 500.0,
        "totalEquityUSD": 20000.0,
        "marketValueUSD": 19500.0,
    }
    result = build_totals_from_balances(balances, stored_exchange_rate=1.38)
    assert result["cashUSD"] == 500.0
    assert result["totalUSD"] == 20000.0


def test_uses_default_exchange_rate_when_stored_rate_is_missing_or_zero():
    balances = {"cashUSDCombined": 100.0, "totalEquityUSDCombined": 1000.0, "marketValueUSDCombined": 900.0}
    result = build_totals_from_balances(balances, stored_exchange_rate=0)
    assert result["exchangeRate"] == 1.3795
