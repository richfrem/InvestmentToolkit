"""Tests for market_data.py's dataQuality wiring (G2, Phase 3 sub-spec 5)."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import _price_staleness, get_prices  # noqa: E402


def test_price_staleness_false_for_empty_rows():
    assert _price_staleness([]) is False


def test_price_staleness_boundary_is_inclusive_not_stale():
    from datetime import datetime, timedelta, timezone
    boundary_date = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()
    assert _price_staleness([{"date": boundary_date, "close": 1.0}], max_age_days=5) is False


def test_price_staleness_true_past_boundary():
    from datetime import datetime, timedelta, timezone
    old_date = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
    assert _price_staleness([{"date": old_date, "close": 1.0}], max_age_days=5) is True


def test_get_prices_attaches_data_quality_on_fresh_fetch():
    with patch("market_data.cache_get", return_value=None), \
         patch("market_data.cache_set"), \
         patch("market_data.yf.download") as mock_download:
        import pandas as pd
        from datetime import date
        idx = pd.to_datetime([date.today().isoformat()])
        mock_download.return_value = pd.DataFrame({
            "Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5], "Volume": [1000],
        }, index=idx)
        result = get_prices(["NVDA"], period="5d")
    assert "dataQuality" in result["NVDA"]
    assert result["NVDA"]["dataQuality"]["staleness"] is False


def test_get_prices_attaches_data_quality_on_cache_hit():
    from datetime import date, timedelta
    stale_date = (date.today() - timedelta(days=30)).isoformat()
    cached_entry = {"data": [{"date": stale_date, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}], "asOf": "x"}
    with patch("market_data.cache_get", return_value=cached_entry):
        result = get_prices(["NVDA"], period="5d")
    assert result["NVDA"]["dataQuality"]["staleness"] is True


def test_get_prices_mixed_cache_and_empty_fetch():
    """Test that cached ticker retains dataQuality key even when fetch batch returns empty.

    Regression test for bug: if some tickers are cache hits and the remaining to-fetch
    batch's yf.download() returns None or empty, the function must still wrap cached
    entries in _with_data_quality(). This tests the early return at line 112.
    """
    from datetime import date, timedelta
    cached_date = (date.today() - timedelta(days=2)).isoformat()
    cached_entry = {
        "data": [{"date": cached_date, "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}],
        "asOf": "x"
    }

    def cache_get_side_effect(key, category):
        if "AAPL" in key and category == "ohlcv":
            return cached_entry
        return None

    import pandas as pd
    with patch("market_data.cache_get", side_effect=cache_get_side_effect), \
         patch("market_data.cache_set"), \
         patch("market_data.yf.download") as mock_download:
        mock_download.return_value = pd.DataFrame()  # Empty DataFrame
        result = get_prices(["AAPL", "MSFT"], period="5d")

    # Both tickers must be in result
    assert "AAPL" in result
    assert "MSFT" not in result  # Not fetched, wasn't cached

    # AAPL was cached and must have dataQuality key
    assert "dataQuality" in result["AAPL"]
    assert "staleness" in result["AAPL"]["dataQuality"]
    assert result["AAPL"]["dataQuality"]["staleness"] is False
