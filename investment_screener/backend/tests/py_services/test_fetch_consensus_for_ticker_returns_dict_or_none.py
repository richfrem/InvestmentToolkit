"""Test _fetch_consensus_for_ticker() graceful NULL handling and error recovery.

Tests the consensus fetcher's contract:
  1. Returns dict with {consensus_eps, consensus_revenue, earnings_date} on success
  2. Returns dict with None values when yfinance has no data
  3. Returns None on API error (rate limit, timeout, etc.)
  4. Retries and falls back gracefully
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from earnings_expectations import _fetch_consensus_for_ticker  # noqa: E402


class TestFetchConsensusForTickerReturnsDict:
    """Consensus data available from yfinance."""

    def test_returns_dict_with_all_fields_when_data_available(self):
        """Should return dict with consensus_eps, consensus_revenue, earnings_date."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": 1.05,
            "totalRevenue": 3.8e11,
        }
        # Mock calendar with a next earnings date
        import pandas as pd
        earnings_date_idx = pd.DatetimeIndex(["2026-07-15"])
        fake_calendar_df = pd.DataFrame(index=["Earnings Date"], columns=earnings_date_idx)
        fake_ticker.calendar = fake_calendar_df

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("AAPL")

        assert result is not None
        assert isinstance(result, dict)
        assert result["consensus_eps"] == 1.05
        assert result["consensus_revenue"] == 3.8e11
        assert result["earnings_date"] == "2026-07-15"

    def test_returns_dict_with_none_consensus_eps_when_missing(self):
        """Should return dict with consensus_eps=None when yfinance has no EPS data."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": None,
            "totalRevenue": 3.8e11,
        }
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("INTC")

        assert result is not None
        assert isinstance(result, dict)
        assert result["consensus_eps"] is None
        assert result["consensus_revenue"] == 3.8e11
        assert result["earnings_date"] is None

    def test_returns_dict_with_none_consensus_revenue_when_missing(self):
        """Should return dict with consensus_revenue=None when yfinance has no revenue."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": 1.05,
            "totalRevenue": None,
        }
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("AMD")

        assert result is not None
        assert isinstance(result, dict)
        assert result["consensus_eps"] == 1.05
        assert result["consensus_revenue"] is None
        assert result["earnings_date"] is None

    def test_returns_dict_with_all_none_when_no_data_available(self):
        """Should return dict with all None when yfinance returns empty info."""
        fake_ticker = MagicMock()
        fake_ticker.info = {}
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("NVDA")

        assert result is not None
        assert isinstance(result, dict)
        assert result["consensus_eps"] is None
        assert result["consensus_revenue"] is None
        assert result["earnings_date"] is None


class TestFetchConsensusForTickerErrorHandling:
    """Test graceful degradation on API errors."""

    def test_returns_none_on_yfinance_api_error(self):
        """Should return None when yfinance raises an exception."""
        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = Exception("API Error")
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("INVALID")

        assert result is None

    def test_returns_none_on_timeout_error(self):
        """Should return None on network timeout."""
        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = TimeoutError("Connection timeout")
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("SYMBOL")

        assert result is None

    def test_returns_none_on_rate_limit_error(self):
        """Should return None when rate limited by yfinance."""
        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = ConnectionError("Rate limited")
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("TICKER")

        assert result is None

    def test_returns_dict_when_earnings_date_fetch_fails_but_consensus_data_available(self):
        """Should still return consensus data if earnings date fetch fails gracefully."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": 0.52,
            "totalRevenue": 9.4e9,
        }
        # Calendar fetch will raise an exception, but should not fail the whole operation
        fake_ticker.calendar = MagicMock(side_effect=Exception("Calendar unavailable"))

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("STOCK")

        assert result is not None
        assert isinstance(result, dict)
        assert result["consensus_eps"] == 0.52
        assert result["consensus_revenue"] == 9.4e9
        assert result["earnings_date"] is None  # Failed gracefully


class TestFetchConsensusForTickerCalendarParsing:
    """Test earnings date extraction from various calendar formats."""

    def test_extracts_earnings_date_from_dataframe_calendar(self):
        """Should extract earnings date from yfinance DataFrame calendar."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": 1.0,
            "totalRevenue": 1e9,
        }
        import pandas as pd
        earnings_idx = pd.DatetimeIndex(["2026-08-20"])
        fake_calendar = pd.DataFrame(index=["Earnings Date"], columns=earnings_idx)
        fake_ticker.calendar = fake_calendar

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("GOOG")

        assert result["earnings_date"] == "2026-08-20"

    def test_extracts_earnings_date_from_dict_calendar(self):
        """Should extract earnings date from dict-format calendar."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": 1.0,
            "totalRevenue": 1e9,
        }
        # Some yfinance versions return calendar as dict
        fake_ticker.calendar = {
            "Earnings Date": ["2026-09-15"],
        }

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("TSLA")

        assert result["earnings_date"] == "2026-09-15"

    def test_handles_missing_calendar_gracefully(self):
        """Should return earnings_date=None when calendar is None."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": 1.0,
            "totalRevenue": 1e9,
        }
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("MSFT")

        assert result["earnings_date"] is None

    def test_handles_empty_calendar_gracefully(self):
        """Should return earnings_date=None when calendar is empty."""
        fake_ticker = MagicMock()
        fake_ticker.info = {
            "epsTrailingTwelveMonths": 1.0,
            "totalRevenue": 1e9,
        }
        import pandas as pd
        # Empty DataFrame
        fake_ticker.calendar = pd.DataFrame()

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("META")

        assert result["earnings_date"] is None


class TestFetchConsensusForTickerReturnType:
    """Verify return type contract."""

    def test_return_type_is_dict_or_none(self):
        """Return value must be dict or None."""
        fake_ticker = MagicMock()
        fake_ticker.info = {"epsTrailingTwelveMonths": 1.0, "totalRevenue": 1e9}
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("GOOD")

        assert isinstance(result, dict) or result is None

    def test_dict_keys_match_contract(self):
        """Returned dict must have expected keys."""
        fake_ticker = MagicMock()
        fake_ticker.info = {"epsTrailingTwelveMonths": 1.0, "totalRevenue": 1e9}
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("SYM")

        assert set(result.keys()) == {"consensus_eps", "consensus_revenue", "earnings_date"}

    def test_consensus_eps_is_float_or_none(self):
        """consensus_eps must be float or None."""
        fake_ticker = MagicMock()
        fake_ticker.info = {"epsTrailingTwelveMonths": 1.5, "totalRevenue": None}
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("TEST")

        assert isinstance(result["consensus_eps"], float) or result["consensus_eps"] is None

    def test_consensus_revenue_is_float_or_none(self):
        """consensus_revenue must be float or None."""
        fake_ticker = MagicMock()
        fake_ticker.info = {"epsTrailingTwelveMonths": None, "totalRevenue": 1.2e10}
        fake_ticker.calendar = None

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("TEST")

        assert isinstance(result["consensus_revenue"], float) or result["consensus_revenue"] is None

    def test_earnings_date_is_iso_string_or_none(self):
        """earnings_date must be ISO format string or None."""
        fake_ticker = MagicMock()
        fake_ticker.info = {"epsTrailingTwelveMonths": 1.0, "totalRevenue": 1e9}
        import pandas as pd
        earnings_idx = pd.DatetimeIndex(["2026-10-30"])
        fake_calendar = pd.DataFrame(index=["Earnings Date"], columns=earnings_idx)
        fake_ticker.calendar = fake_calendar

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = fake_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = _fetch_consensus_for_ticker("TEST")

        if result["earnings_date"] is not None:
            # Verify ISO format YYYY-MM-DD
            assert isinstance(result["earnings_date"], str)
            assert len(result["earnings_date"]) == 10
            assert result["earnings_date"].count("-") == 2
