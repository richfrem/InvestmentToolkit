import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_prices  # noqa: E402


def _fake_yf_download():
    idx = pd.to_datetime(["2026-07-01", "2026-07-02"])
    cols = pd.MultiIndex.from_tuples(
        [("Open", "AAPL"), ("High", "AAPL"), ("Low", "AAPL"), ("Close", "AAPL"), ("Volume", "AAPL")]
    )
    return pd.DataFrame(
        [[199.0, 201.0, 198.0, 200.0, 1000000], [200.0, 203.0, 199.5, 202.0, 1200000]],
        index=idx, columns=cols,
    )


def test_get_prices_returns_source_tagged_ohlcv(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    with patch("market_data.yf.download", return_value=_fake_yf_download()):
        result = get_prices(["AAPL"], period="5d")

    assert result["AAPL"]["source"] == "yfinance"
    assert len(result["AAPL"]["data"]) == 2
    assert result["AAPL"]["data"][-1]["close"] == 202.0


def test_get_prices_uses_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr("market_data.CACHE_DIR", tmp_path)
    with patch("market_data.yf.download", return_value=_fake_yf_download()) as mock_dl:
        get_prices(["AAPL"], period="5d")
        result = get_prices(["AAPL"], period="5d")

    mock_dl.assert_called_once()
    assert result["AAPL"]["source"] == "cache"
