#!/usr/bin/env python3
"""
technicals.py (Python Service)
=====================================

Purpose:
    Headless local TA engine — hand-rolled implementations (no TA libraries)
    of RSI(14) Wilder, EMA 21/50/200, MACD, ADX(14), ATR(14), Bollinger/
    Keltner squeeze, anchored VWAP, 20d volume ratio, and relative strength
    vs. a benchmark. Computes from OHLCV supplied by market_data.get_prices()
    (yfinance-backed) — never TradingView CDP, which can only read the
    currently-active chart (pitfall #7 in CLAUDE.md) and has no batch/
    background history endpoint. TV is used only as the trust-check, via
    ta_sweep_batch.py --validate (Phase 2b, separate task).

Layer: Backend / Python Services / Technical Analysis

Usage:
    python3 technicals.py --ticker NVDA --timeframe D --period 1y --benchmark SPY --pretty
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_prices  # noqa: E402


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing: seed with a simple mean of the first `period` values,
    then recursively blend as (prev * (period - 1) + current) / period.

    Args:
        series: Raw per-bar values to smooth (e.g. gains, losses, true range).
        period: Smoothing period (e.g. 14).

    Returns:
        A pandas Series of the same length, with NaN for the first
        `period - 1` bars (insufficient data to seed the average).
    """
    result = pd.Series(index=series.index, dtype=float)
    if len(series) < period:
        return result
    result.iloc[period - 1] = series.iloc[:period].mean()
    for i in range(period, len(series)):
        result.iloc[i] = (result.iloc[i - 1] * (period - 1) + series.iloc[i]) / period
    return result


def compute_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """RSI(14) with Wilder smoothing — the standard, non-EMA-smoothed formula.

    Args:
        closes: Close prices, oldest first.
        period: RSI lookback period, default 14.

    Returns:
        Latest RSI value in [0, 100], or None if fewer than period+1 bars.
    """
    if len(closes) < period + 1:
        return None
    delta = closes.diff().dropna()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = _wilder_smooth(gains, period).iloc[-1]
    avg_loss = _wilder_smooth(losses, period).iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_ema(closes: pd.Series, period: int) -> float | None:
    """Exponential moving average, latest value.

    Args:
        closes: Close prices, oldest first.
        period: EMA span (e.g. 21, 50, 200).

    Returns:
        Latest EMA value, or None if fewer than `period` bars.
    """
    if len(closes) < period:
        return None
    return round(closes.ewm(span=period, adjust=False).mean().iloc[-1], 4)


def compute_macd(closes: pd.Series) -> dict:
    """MACD(12,26,9): fast EMA minus slow EMA, plus a signal EMA of that line.

    Args:
        closes: Close prices, oldest first.

    Returns:
        {"line": float, "signal": float, "histogram": float}, using whatever
        data is available (no minimum-length guard beyond what ewm() itself
        requires — MACD degrades gracefully on shorter series).
    """
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "line": round(macd_line.iloc[-1], 4),
        "signal": round(signal_line.iloc[-1], 4),
        "histogram": round(histogram.iloc[-1], 4),
    }


def _true_range(highs: pd.Series, lows: pd.Series, closes: pd.Series) -> pd.Series:
    """Per-bar true range: max(high-low, |high-prev_close|, |low-prev_close|)."""
    prev_close = closes.shift(1)
    return pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs(),
    ], axis=1).max(axis=1)


def compute_atr(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> float | None:
    """Average True Range (Wilder-smoothed), latest value.

    Args:
        highs: High prices, oldest first.
        lows: Low prices, oldest first.
        closes: Close prices, oldest first.
        period: ATR lookback period, default 14.

    Returns:
        Latest ATR value (>= 0), or None if fewer than period+1 bars.
    """
    if len(closes) < period + 1:
        return None
    tr = _true_range(highs, lows, closes).dropna()
    atr = _wilder_smooth(tr, period).iloc[-1]
    return round(float(atr), 4)


def compute_adx(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> dict:
    """ADX(14) with +DI/-DI, Wilder-smoothed throughout.

    Args:
        highs: High prices, oldest first.
        lows: Low prices, oldest first.
        closes: Close prices, oldest first.
        period: ADX lookback period, default 14.

    Returns:
        {"adx14": float|None, "plusDI": float|None, "minusDI": float|None}.
        None across all three if fewer than 2*period bars (ADX needs a
        smoothed DX series on top of the smoothed DM/TR series).
    """
    if len(closes) < period * 2:
        return {"adx14": None, "plusDI": None, "minusDI": None}

    up_move = highs.diff()
    down_move = -lows.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=highs.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=highs.index)
    tr = _true_range(highs, lows, closes)

    smoothed_tr = _wilder_smooth(tr.dropna(), period)
    smoothed_plus_dm = _wilder_smooth(plus_dm.dropna(), period)
    smoothed_minus_dm = _wilder_smooth(minus_dm.dropna(), period)

    plus_di = 100 * smoothed_plus_dm / smoothed_tr
    minus_di = 100 * smoothed_minus_dm / smoothed_tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = _wilder_smooth(dx.dropna(), period)

    return {
        "adx14": round(float(adx.iloc[-1]), 2),
        "plusDI": round(float(plus_di.iloc[-1]), 2),
        "minusDI": round(float(minus_di.iloc[-1]), 2),
    }


def main() -> None:
    """CLI entry point — wired fully in Task 6 once squeeze/VWAP/RS are added."""
    parser = argparse.ArgumentParser(description="Local TA engine")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--timeframe", default="D", choices=["D", "W"])
    parser.add_argument("--period", default="1y")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    interval = "1d" if args.timeframe == "D" else "1wk"
    prices = get_prices([args.ticker], period=args.period, interval=interval)
    rows = prices.get(args.ticker, {}).get("data", [])
    df = pd.DataFrame(rows)
    result = {
        "ticker": args.ticker,
        "timeframe": args.timeframe,
        "rsi14": compute_rsi(df["close"]) if not df.empty else None,
        "ema21": compute_ema(df["close"], 21) if not df.empty else None,
        "ema50": compute_ema(df["close"], 50) if not df.empty else None,
        "ema200": compute_ema(df["close"], 200) if not df.empty else None,
        "macd": compute_macd(df["close"]) if not df.empty else None,
        "atr14": compute_atr(df["high"], df["low"], df["close"]) if not df.empty else None,
        **(compute_adx(df["high"], df["low"], df["close"]) if not df.empty else
           {"adx14": None, "plusDI": None, "minusDI": None}),
    }
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
