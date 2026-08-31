"""
Caught live 2026-08-29: across three tickers in one session (BE, BTDR, CBRS),
fetch_financials.py's metrics.profit_margin (from yfinance's info['profitMargins'])
disagreed wildly with financials.historical_net_margin's TTM entry (computed
locally from historical_revenue/historical_net_income) -- e.g. BE: -4.37% vs
+7.87%; BTDR: +10.58% vs -28.14%; CBRS: +46.63% vs -75.27%. Neither figure is
wrong per se (they're two different Yahoo Finance data endpoints that can
disagree due to fiscal-period/restatement differences), but nothing flagged
the disagreement -- it had to be manually caught by eye each time, costing
real reasoning effort on every single ticker. check_margin_consistency() makes
this an automatic, machine-readable flag instead.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_fetch_financials_margin_flag.py -v
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from fetch_financials import check_margin_consistency  # noqa: E402


def test_flags_large_disagreement():
    """BE's real case: -4.37% vs +7.87% (12.24pp gap) -- should flag."""
    flags = check_margin_consistency(profit_margin_pct=7.87, historical_net_margin_ttm_pct=-4.37)
    assert len(flags) == 1
    assert "profit_margin" in flags[0] and "historical_net_margin" in flags[0]


def test_flags_extreme_disagreement():
    """CBRS's real case: +46.63% vs -75.27% (121.9pp gap) -- must flag."""
    flags = check_margin_consistency(profit_margin_pct=-75.27, historical_net_margin_ttm_pct=46.63)
    assert len(flags) == 1


def test_no_flag_when_values_agree():
    """Small, expected rounding/timing differences must not flag."""
    flags = check_margin_consistency(profit_margin_pct=15.2, historical_net_margin_ttm_pct=15.8)
    assert flags == []


def test_no_flag_when_either_value_missing():
    """A missing/zero field (common for newly-listed or thinly-covered tickers)
    must not produce a spurious flag comparing against a real 0.0."""
    assert check_margin_consistency(profit_margin_pct=0.0, historical_net_margin_ttm_pct=-4.37) == []
    assert check_margin_consistency(profit_margin_pct=7.87, historical_net_margin_ttm_pct=0.0) == []


if __name__ == "__main__":
    test_flags_large_disagreement()
    test_flags_extreme_disagreement()
    test_no_flag_when_values_agree()
    test_no_flag_when_either_value_missing()
    print("✓ All fetch_financials margin-flag tests passed!")
