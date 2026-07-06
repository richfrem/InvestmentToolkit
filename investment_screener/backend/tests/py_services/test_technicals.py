"""Tests for technicals.py — local TA engine, hand-rolled indicators (Phase 2b)."""
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from technicals import compute_adx, compute_atr, compute_ema, compute_macd, compute_rsi  # noqa: E402
from technicals import (  # noqa: E402
    compute_anchored_vwap,
    compute_bollinger_keltner_squeeze,
    compute_relative_strength,
    compute_technical_snapshot,
    compute_volume_ratio,
)


def _constant_series(value: float, n: int = 60) -> pd.Series:
    return pd.Series([value] * n)


def _uptrend_series(start: float, step: float, n: int = 60) -> pd.Series:
    return pd.Series([start + step * i for i in range(n)])


# ── RSI ────────────────────────────────────────────────────────────────────

def test_rsi_is_bounded_0_to_100_property():
    closes = pd.Series([100, 102, 101, 105, 103, 108, 107, 110, 106, 112,
                         115, 111, 118, 116, 120, 119, 122, 121, 125, 124] * 3)
    rsi = compute_rsi(closes, period=14)
    assert 0.0 <= rsi <= 100.0


def test_rsi_all_gains_scores_100():
    closes = _uptrend_series(start=100, step=1, n=20)
    rsi = compute_rsi(closes, period=14)
    assert rsi == 100.0


def test_rsi_returns_none_for_insufficient_data():
    closes = pd.Series([100, 101, 102])
    assert compute_rsi(closes, period=14) is None


# ── EMA ────────────────────────────────────────────────────────────────────

def test_ema_converges_to_price_under_constant_series():
    closes = _constant_series(150.0, n=250)
    assert compute_ema(closes, period=21) == 150.0
    assert compute_ema(closes, period=200) == 150.0


# ── MACD ───────────────────────────────────────────────────────────────────

def test_macd_returns_line_signal_histogram_shape():
    closes = _uptrend_series(start=100, step=0.5, n=60)
    macd = compute_macd(closes)
    assert set(macd.keys()) == {"line", "signal", "histogram"}
    assert round(macd["line"] - macd["signal"], 6) == round(macd["histogram"], 6)


def test_macd_line_is_zero_under_constant_series():
    closes = _constant_series(150.0, n=60)
    macd = compute_macd(closes)
    assert macd["line"] == 0.0


# ── ATR ────────────────────────────────────────────────────────────────────

def test_atr_is_non_negative_property():
    highs = _uptrend_series(105, 1, n=30)
    lows = _uptrend_series(95, 1, n=30)
    closes = _uptrend_series(100, 1, n=30)
    atr = compute_atr(highs, lows, closes, period=14)
    assert atr >= 0.0


def test_atr_is_zero_under_flat_no_range_series():
    highs = _constant_series(100.0, n=30)
    lows = _constant_series(100.0, n=30)
    closes = _constant_series(100.0, n=30)
    assert compute_atr(highs, lows, closes, period=14) == 0.0


# ── ADX ────────────────────────────────────────────────────────────────────

def test_adx_returns_shape_and_bounded_range():
    highs = _uptrend_series(105, 1.5, n=40)
    lows = _uptrend_series(95, 1.5, n=40)
    closes = _uptrend_series(100, 1.5, n=40)
    result = compute_adx(highs, lows, closes, period=14)
    assert set(result.keys()) == {"adx14", "plusDI", "minusDI"}
    assert 0.0 <= result["adx14"] <= 100.0
    assert result["plusDI"] > result["minusDI"]  # clean uptrend -> +DI dominates


# ── Bollinger/Keltner squeeze ─────────────────────────────────────────────────

def test_squeeze_true_when_bollinger_inside_keltner():
    # Very low volatility closes -> tight Bollinger bands, squeezed inside Keltner.
    closes = _constant_series(100.0, n=30) + pd.Series([0.01 * (i % 2) for i in range(30)])
    highs = closes + 0.05
    lows = closes - 0.05
    result = compute_bollinger_keltner_squeeze(closes, highs, lows, atr14=0.5)
    assert result["squeeze"] is True


def test_squeeze_false_when_bollinger_outside_keltner():
    closes = _uptrend_series(100, 3, n=30)  # wide bands from a strong trend
    highs = closes + 1.0
    lows = closes - 1.0
    result = compute_bollinger_keltner_squeeze(closes, highs, lows, atr14=0.5)
    assert result["squeeze"] is False


# ── Anchored VWAP ──────────────────────────────────────────────────────────────

def test_anchored_vwap_computes_from_anchor_date_forward():
    dates = pd.Series(["2026-01-01", "2026-01-02", "2026-01-03"])
    highs = pd.Series([102.0, 104.0, 106.0])
    lows = pd.Series([98.0, 100.0, 102.0])
    closes = pd.Series([100.0, 102.0, 104.0])
    volumes = pd.Series([1000.0, 1000.0, 1000.0])
    vwap = compute_anchored_vwap(highs, lows, closes, volumes, dates, anchor_date="2026-01-02")
    # Only bars on/after 2026-01-02 count: typical prices (104+100+102)/3=102, (106+102+104)/3=104
    expected = (102.0 * 1000 + 104.0 * 1000) / (1000 + 1000)
    assert round(vwap, 4) == round(expected, 4)


def test_anchored_vwap_returns_none_when_anchor_date_not_found():
    dates = pd.Series(["2026-01-01", "2026-01-02"])
    highs = pd.Series([102.0, 104.0])
    lows = pd.Series([98.0, 100.0])
    closes = pd.Series([100.0, 102.0])
    volumes = pd.Series([1000.0, 1000.0])
    assert compute_anchored_vwap(highs, lows, closes, volumes, dates, anchor_date="2099-01-01") is None


# ── Volume ratio ───────────────────────────────────────────────────────────────

def test_volume_ratio_above_one_on_volume_spike():
    volumes = pd.Series([1000.0] * 20 + [3000.0])
    assert compute_volume_ratio(volumes, period=20) == 3.0


def test_volume_ratio_returns_none_for_insufficient_data():
    volumes = pd.Series([1000.0] * 5)
    assert compute_volume_ratio(volumes, period=20) is None


# ── Relative strength ──────────────────────────────────────────────────────────

def test_relative_strength_ratio_above_one_when_outperforming():
    ticker_closes = _uptrend_series(100, 2, n=70)
    benchmark_closes = _uptrend_series(100, 0.5, n=70)
    result = compute_relative_strength(ticker_closes, benchmark_closes)
    assert result["ratio"] > 1.0
    assert result["slope63d"] > 0


# ── Full snapshot orchestration ────────────────────────────────────────────────

def test_compute_technical_snapshot_shape():
    rows = [
        {"date": f"2026-01-{i+1:02d}", "open": 100 + i, "high": 102 + i,
         "low": 98 + i, "close": 100 + i, "volume": 1000.0}
        for i in range(60)
    ]
    fake_prices = {"NVDA": {"data": rows}, "SPY": {"data": rows}}
    with patch("technicals.get_prices", return_value=fake_prices), \
         patch("technicals.get_earnings_calendar", return_value=[]):
        snapshot = compute_technical_snapshot("NVDA", "D", "1y", "SPY", anchor_date=None)

    expected_keys = {
        "ticker", "timeframe", "asOf", "rsi14", "ema21", "ema50", "ema200",
        "macd", "adx14", "plusDI", "minusDI", "atr14", "bollinger", "keltner",
        "squeeze", "anchoredVwap", "volumeRatio20d", "relativeStrength",
    }
    assert expected_keys <= set(snapshot.keys())
    assert snapshot["ticker"] == "NVDA"
