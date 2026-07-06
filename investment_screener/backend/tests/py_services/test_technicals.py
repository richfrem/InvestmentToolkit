"""Tests for technicals.py — local TA engine, hand-rolled indicators (Phase 2b)."""
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from technicals import compute_adx, compute_atr, compute_ema, compute_macd, compute_rsi  # noqa: E402


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
