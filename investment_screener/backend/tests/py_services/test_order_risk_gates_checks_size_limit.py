"""Tests for order_risk_gates.py — get_average_daily_volume() and
check_order_size() (Task 5E-4).

check_order_size() is a liquidity/market-impact safeguard: it checks
whether a single, ad-hoc order's share count exceeds a safe percentage
of the ticker's average daily trading volume. Distinct from Task
5D-8's compute_liquidity_score() (a single TV candle's Volume as a
rough intraday proxy) — this gate uses REAL multi-day average daily
volume fetched via market_data.py's get_prices() (Phase 1's real,
cached yfinance data layer), reused here rather than calling yfinance
directly a second time.

get_average_daily_volume() mocks market_data.get_prices() in every
test — no test in this file ever hits real yfinance/network calls.
check_order_size() tests pass daily_volume explicitly wherever
possible to isolate them from get_average_daily_volume()'s own tests.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import market_data  # noqa: E402
import order_risk_gates  # noqa: E402
from order_risk_gates import check_order_size, get_average_daily_volume  # noqa: E402


def _order(ticker="CORZ", shares=500.0):
    return {"ticker": ticker, "shares": shares}


# --- check_order_size() ------------------------------------------------


def test_check_order_size_passes_within_limit():
    """shares=500 / daily_volume=1_000_000 = 0.05%, well within the 10% default cap."""
    order = _order(shares=500.0)

    result = check_order_size(order, daily_volume=1_000_000)

    assert result["passed"] is True
    assert result["size_pct_of_volume"] == 0.05


def test_check_order_size_fails_exceeding_limit():
    """shares=200_000 / daily_volume=1_000_000 = 20%, over the 10% default cap."""
    order = _order(shares=200_000.0)

    result = check_order_size(order, daily_volume=1_000_000)

    assert result["passed"] is False
    assert result["size_pct_of_volume"] == 20.0


def test_check_order_size_uses_custom_max_pct():
    """max_pct_of_volume=5.0 is respected instead of the 10.0 default."""
    # 60_000 / 1_000_000 = 6% -> passes default 10% cap, fails custom 5% cap.
    order = _order(shares=60_000.0)

    default_result = check_order_size(order, daily_volume=1_000_000)
    assert default_result["passed"] is True

    custom_result = check_order_size(order, daily_volume=1_000_000, max_pct_of_volume=5.0)
    assert custom_result["passed"] is False
    assert custom_result["size_pct_of_volume"] == 6.0


def test_check_order_size_boundary_at_exact_cap_passes():
    """An order sized to EXACTLY max_pct_of_volume passes (> not >=)."""
    # 100_000 / 1_000_000 = 10% exactly.
    order = _order(shares=100_000.0)

    result = check_order_size(order, daily_volume=1_000_000, max_pct_of_volume=10.0)

    assert result["passed"] is True
    assert result["size_pct_of_volume"] == 10.0


def test_check_order_size_handles_missing_daily_volume(monkeypatch):
    """daily_volume=None and get_average_daily_volume (mocked) returns None -> passes, no exception."""
    monkeypatch.setattr(order_risk_gates, "get_average_daily_volume", lambda ticker, days=10: None)
    order = _order(shares=500.0)

    result = check_order_size(order, daily_volume=None)

    assert result["passed"] is True
    assert result["size_pct_of_volume"] is None


def test_check_order_size_handles_zero_daily_volume():
    """A genuinely zero/no-trading-volume day shouldn't crash a division — passes."""
    order = _order(shares=500.0)

    result = check_order_size(order, daily_volume=0)

    assert result["passed"] is True
    assert result["size_pct_of_volume"] is None


def test_check_order_size_fetches_volume_when_not_supplied(monkeypatch):
    """daily_volume=None triggers a call to get_average_daily_volume() with the order's ticker."""
    calls = []

    def fake_get_average_daily_volume(ticker, days=10):
        calls.append(ticker)
        return 1_000_000

    monkeypatch.setattr(order_risk_gates, "get_average_daily_volume", fake_get_average_daily_volume)
    order = _order(ticker="NBIS", shares=200_000.0)

    result = check_order_size(order, daily_volume=None)

    assert calls == ["NBIS"]
    assert result["passed"] is False
    assert result["size_pct_of_volume"] == 20.0


# --- get_average_daily_volume() -----------------------------------------


def test_get_average_daily_volume_computes_correct_average(monkeypatch):
    """3 days of volume data [1000, 2000, 3000] -> average 2000."""
    def fake_get_prices(tickers, period, interval="1d"):
        return {
            "CORZ": {
                "data": [
                    {"date": "2026-07-08", "volume": 1000},
                    {"date": "2026-07-09", "volume": 2000},
                    {"date": "2026-07-10", "volume": 3000},
                ],
                "source": "yfinance",
                "asOf": "2026-07-10T00:00:00+00:00",
            }
        }

    monkeypatch.setattr(market_data, "get_prices", fake_get_prices)

    result = get_average_daily_volume("CORZ")

    assert result == 2000


def test_get_average_daily_volume_returns_none_on_empty_data(monkeypatch):
    """Ticker missing from result entirely (or an empty 'data' list) -> None, no exception."""
    def fake_get_prices(tickers, period, interval="1d"):
        return {"CORZ": {"data": [], "source": "yfinance", "asOf": "2026-07-10T00:00:00+00:00"}}

    monkeypatch.setattr(market_data, "get_prices", fake_get_prices)

    assert get_average_daily_volume("CORZ") is None

    def fake_get_prices_missing_ticker(tickers, period, interval="1d"):
        return {}

    monkeypatch.setattr(market_data, "get_prices", fake_get_prices_missing_ticker)

    assert get_average_daily_volume("CORZ") is None


def test_get_average_daily_volume_returns_none_on_fetch_exception(monkeypatch):
    """get_prices raising -> get_average_daily_volume() returns None, no exception propagates."""
    def fake_get_prices(tickers, period, interval="1d"):
        raise RuntimeError("network error")

    monkeypatch.setattr(market_data, "get_prices", fake_get_prices)

    assert get_average_daily_volume("CORZ") is None


def test_get_average_daily_volume_respects_custom_days_parameter(monkeypatch):
    """days=5 -> get_prices() called with period='5d'."""
    captured = {}

    def fake_get_prices(tickers, period, interval="1d"):
        captured["period"] = period
        captured["tickers"] = tickers
        captured["interval"] = interval
        return {"CORZ": {"data": [{"date": "2026-07-10", "volume": 500}], "source": "yfinance", "asOf": ""}}

    monkeypatch.setattr(market_data, "get_prices", fake_get_prices)

    get_average_daily_volume("CORZ", days=5)

    assert captured["period"] == "5d"
    assert captured["tickers"] == ["CORZ"]
