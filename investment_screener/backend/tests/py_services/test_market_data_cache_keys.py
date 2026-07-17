"""Regression test: get_estimates() and get_fundamentals() must not share a cache key.

Both previously called cache_get/cache_set(ticker, "fundamentals") — whichever ran second for a
given ticker silently overwrote the other's cache entry, defeating caching for any pipeline (e.g.
a full /evaluate-stock pass) that needs both.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_estimates, get_fundamentals  # noqa: E402
import cache  # noqa: E402


def _fake_estimates_ticker():
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame(
        {"avg": [7716355790.0, 11197459210.0]}, index=["0y", "+1y"]
    )
    return fake_ticker


def _fake_fundamentals_ticker():
    fake_ticker = MagicMock()
    fake_ticker.info = {"totalRevenue": 395000000000.0, "netIncomeToCommon": 94000000000.0}
    fake_ticker.financials = pd.DataFrame(
        {pd.Timestamp("2025-09-27"): [395000000000.0, 94000000000.0]},
        index=["Total Revenue", "Net Income"],
    )
    return fake_ticker


def test_get_estimates_and_get_fundamentals_do_not_collide_for_same_ticker(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)

    with patch("market_data.yf.Ticker", return_value=_fake_estimates_ticker()):
        estimates_result = get_estimates("PLTR")

    with patch("market_data.yf.Ticker", return_value=_fake_fundamentals_ticker()):
        fundamentals_result = get_fundamentals("PLTR", cik=None)

    # Both cache entries must exist independently, under distinct data-class keys.
    cached_estimates = cache.cache_get("PLTR", "estimates")
    cached_fundamentals = cache.cache_get("PLTR", "fundamentals")

    assert cached_estimates is not None, "estimates cache entry was never written or was overwritten"
    assert cached_fundamentals is not None, "fundamentals cache entry was never written or was overwritten"
    assert "y1RevEstimate" in cached_estimates
    assert "revenue" in cached_fundamentals

    # Re-fetching each must hit its own cache, not the other's data
    assert estimates_result["y1RevEstimate"] == 7716355790.0
    assert fundamentals_result["revenue"]["value"] == 395000000000.0


def test_calling_get_fundamentals_after_get_estimates_does_not_clobber_estimates_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)

    with patch("market_data.yf.Ticker", return_value=_fake_estimates_ticker()):
        get_estimates("NVDA")

    with patch("market_data.yf.Ticker", return_value=_fake_fundamentals_ticker()):
        get_fundamentals("NVDA", cik=None)

    # The estimates cache entry must still be readable and correct after fundamentals was cached.
    cached_estimates = cache.cache_get("NVDA", "estimates")
    assert cached_estimates is not None
    assert cached_estimates["y1RevEstimate"] == 7716355790.0
