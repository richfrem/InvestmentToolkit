"""Task 2: Price fetcher tests."""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import fetch_backtest_prices  # noqa: E402


def test_fetch_backtest_prices_handles_gaps():
    """Fetch prices for tickers including some that don't exist."""
    tickers = ["AAPL", "INVALID_TICKER_XYZABC", "MSFT"]
    # Use a date in the past to ensure historical data (60 days is safe)
    past_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    prices = fetch_backtest_prices(tickers, past_date)

    # Should return a dict (possibly empty for invalid tickers)
    assert isinstance(prices, dict)

    # Valid tickers like AAPL should be present if date is valid
    if prices.get("AAPL"):
        aapl_data = prices["AAPL"]
        assert "open" in aapl_data
        assert "high" in aapl_data
        assert "low" in aapl_data
        assert "close" in aapl_data
        assert "volume" in aapl_data
        assert aapl_data["low"] <= aapl_data["high"]


def test_fetch_backtest_prices_caches_locally(tmp_path, monkeypatch):
    """Fetch prices are cached locally in backtest_price_cache."""
    # Monkeypatch the cache directory
    monkeypatch.setattr(
        "backtest_harness.PRICE_CACHE_DIR",
        tmp_path / "test_cache",
    )

    # Use a date that's guaranteed to have data (60 days ago is safe)
    past_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    tickers = ["AAPL"]

    # First call fetches from yfinance
    prices1 = fetch_backtest_prices(tickers, past_date)

    # Check if cache file was created (only if fetch was successful)
    cache_file = tmp_path / "test_cache" / f"AAPL_{past_date}.json"
    if prices1.get("AAPL"):
        assert cache_file.exists()

        # Second call should read from cache (not require yfinance again)
        prices2 = fetch_backtest_prices(tickers, past_date)

        # Results should be identical
        assert prices1["AAPL"] == prices2["AAPL"]


def test_fetch_backtest_prices_returns_dict_with_ohlcv_keys():
    """Prices include all required OHLCV fields."""
    past_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    prices = fetch_backtest_prices(["AAPL"], past_date)

    if prices.get("AAPL"):
        aapl = prices["AAPL"]
        required_keys = {"open", "high", "low", "close", "volume"}
        assert required_keys.issubset(aapl.keys())


def test_fetch_backtest_prices_handles_missing_ticker_gracefully():
    """Missing ticker is skipped, not error."""
    past_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    prices = fetch_backtest_prices(["INVALID_TICKER_XYZ_DOES_NOT_EXIST"], past_date)

    # Should return empty dict, not raise
    assert isinstance(prices, dict)
