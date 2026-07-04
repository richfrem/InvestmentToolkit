import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_estimates  # noqa: E402


def test_get_estimates_returns_y1_and_y2_revenue(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame(
        {"avg": [7716355790.0, 11197459210.0]}, index=["0y", "+1y"]
    )
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("PLTR")

    assert result["y1RevEstimate"] == 7716355790.0
    assert result["y2RevEstimate"] == 11197459210.0
    assert result["source"] == "yfinance"


def test_get_estimates_returns_none_fields_when_data_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame()
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("OBSCURE")

    assert result["y1RevEstimate"] is None
    assert result["y2RevEstimate"] is None


def test_get_estimates_uses_cache_within_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame(
        {"avg": [7716355790.0, 11197459210.0]}, index=["0y", "+1y"]
    )
    with patch("market_data.yf.Ticker", return_value=fake_ticker) as mock_ticker:
        get_estimates("PLTR")
        result = get_estimates("PLTR")

    mock_ticker.assert_called_once()
    assert result["source"] == "cache"
    assert result["y1RevEstimate"] == 7716355790.0


def test_get_estimates_handles_nan_avg_value_without_crashing(tmp_path, monkeypatch):
    """A populated row whose 'avg' is NaN (real-world yfinance gap, not a missing
    row) must degrade to None for that field, not raise and not become 0.0.
    """
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame(
        {"avg": [float("nan"), 11197459210.0]}, index=["0y", "+1y"]
    )
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("HALFDATA")

    assert result["y1RevEstimate"] is None
    assert result["y2RevEstimate"] == 11197459210.0


def test_get_estimates_handles_missing_avg_column_without_crashing(tmp_path, monkeypatch):
    """A DataFrame that has rows but not the expected 'avg' column (schema drift
    from yfinance) must not raise a KeyError.
    """
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = pd.DataFrame(
        {"low": [1.0, 2.0], "high": [3.0, 4.0]}, index=["0y", "+1y"]
    )
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("NOAVGCOL")

    assert result["y1RevEstimate"] is None
    assert result["y2RevEstimate"] is None


def test_get_estimates_handles_none_dataframe_without_crashing(tmp_path, monkeypatch):
    """yfinance can return None instead of an empty DataFrame for tickers with no
    analyst coverage at all. Must not raise AttributeError on .empty/.index.
    """
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.revenue_estimate = None
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("NODATA")

    assert result["y1RevEstimate"] is None
    assert result["y2RevEstimate"] is None


def test_get_estimates_handles_property_raising_without_crashing(tmp_path, monkeypatch):
    """If accessing .revenue_estimate itself raises (network error, yfinance
    internal parsing failure, etc.), get_estimates must degrade to None fields
    rather than propagate the exception and kill the caller.
    """
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    type(fake_ticker).revenue_estimate = property(
        lambda self: (_ for _ in ()).throw(RuntimeError("yfinance boom"))
    )
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_estimates("BOOM")

    assert result["y1RevEstimate"] is None
    assert result["y2RevEstimate"] is None
    assert result["source"] == "yfinance"
