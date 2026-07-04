import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import cache  # noqa: E402
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


def _fake_yf_download_misaligned_calendar():
    """Two tickers on different exchanges (e.g. NASDAQ + TSX): one has a real
    NaN row (not a missing key) for the date it didn't trade, the other has
    full data for both dates — reproducing yfinance's outer-join behavior on
    misaligned trading calendars."""
    idx = pd.to_datetime(["2026-07-01", "2026-07-02"])
    cols = pd.MultiIndex.from_tuples([
        ("Open", "AAPL"), ("High", "AAPL"), ("Low", "AAPL"), ("Close", "AAPL"), ("Volume", "AAPL"),
        ("Open", "PSU-U.TO"), ("High", "PSU-U.TO"), ("Low", "PSU-U.TO"), ("Close", "PSU-U.TO"), ("Volume", "PSU-U.TO"),
    ])
    return pd.DataFrame(
        [
            [199.0, 201.0, 198.0, 200.0, 1000000, 100.0, 101.0, 99.0, 100.5, 5000],
            [200.0, 203.0, 199.5, 202.0, 1200000, float("nan"), float("nan"), float("nan"), float("nan"), float("nan")],
        ],
        index=idx, columns=cols,
    )


def test_get_prices_returns_source_tagged_ohlcv(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    with patch("market_data.yf.download", return_value=_fake_yf_download()):
        result = get_prices(["AAPL"], period="5d")

    assert result["AAPL"]["source"] == "yfinance"
    assert len(result["AAPL"]["data"]) == 2
    assert result["AAPL"]["data"][-1]["close"] == 202.0


def test_get_prices_uses_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    with patch("market_data.yf.download", return_value=_fake_yf_download()) as mock_dl:
        get_prices(["AAPL"], period="5d")
        result = get_prices(["AAPL"], period="5d")

    mock_dl.assert_called_once()
    assert result["AAPL"]["source"] == "cache"


def test_get_prices_skips_nan_rows_on_misaligned_trading_calendar(tmp_path, monkeypatch):
    """PSU-U.TO (TSX) didn't trade on 2026-07-02 while AAPL (NASDAQ) did.
    yfinance's multi-ticker download outer-joins the two frames, leaving a
    real NaN row for PSU-U.TO on that date. get_prices() must not crash on
    int(NaN)/float(NaN) and must not zero-fill — it should simply omit that
    row for PSU-U.TO while keeping AAPL's full history."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    with patch("market_data.yf.download", return_value=_fake_yf_download_misaligned_calendar()):
        result = get_prices(["AAPL", "PSU-U.TO"], period="5d")

    assert len(result["AAPL"]["data"]) == 2
    assert len(result["PSU-U.TO"]["data"]) == 1
    assert len(result["PSU-U.TO"]["data"]) < len(result["AAPL"]["data"])
    assert result["PSU-U.TO"]["data"][0]["close"] == 100.5
