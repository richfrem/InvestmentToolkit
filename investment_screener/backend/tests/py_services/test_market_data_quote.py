import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_quote  # noqa: E402


def test_get_quote_returns_source_tagged_price(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.fast_info = {"lastPrice": 205.5}
    with patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_quote(["AAPL"])

    assert result["AAPL"]["price"] == 205.5
    assert result["AAPL"]["source"] == "yfinance"


def test_get_quote_uses_cache_within_15_minutes(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.fast_info = {"lastPrice": 205.5}
    with patch("market_data.yf.Ticker", return_value=fake_ticker) as mock_ticker:
        get_quote(["AAPL"])
        result = get_quote(["AAPL"])

    mock_ticker.assert_called_once()
    assert result["AAPL"]["source"] == "cache"


def test_get_quote_skips_bad_ticker_without_crashing_batch(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    good_ticker = MagicMock()
    good_ticker.fast_info = {"lastPrice": 100.0}
    bad_ticker = MagicMock()
    bad_ticker.fast_info = {}  # missing "lastPrice" -> None -> float(None) would raise TypeError

    def fake_ticker_factory(symbol):
        return bad_ticker if symbol == "BAD" else good_ticker

    with patch("market_data.yf.Ticker", side_effect=fake_ticker_factory):
        result = get_quote(["GOOD", "BAD"])

    assert result["GOOD"]["price"] == 100.0
    assert "BAD" not in result
