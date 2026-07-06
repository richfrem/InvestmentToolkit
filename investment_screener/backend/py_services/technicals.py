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
from earnings_calendar import get_earnings_calendar  # noqa: E402


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


def compute_bollinger_keltner_squeeze(
    closes: pd.Series, highs: pd.Series, lows: pd.Series, atr14: float, period: int = 20
) -> dict:
    """Bollinger(20,2) and Keltner(20, 1.5xATR14) bands, plus squeeze detection.

    Squeeze is True when the Bollinger Bands sit entirely inside the Keltner
    Channel — the standard TTM Squeeze definition, signaling a volatility
    contraction that often precedes a breakout.

    Args:
        closes: Close prices, oldest first.
        highs: High prices, oldest first (unused directly, kept for interface symmetry).
        lows: Low prices, oldest first (unused directly, kept for interface symmetry).
        atr14: Precomputed ATR(14) value, used as the Keltner band width.
        period: SMA/EMA period for both bands' midline, default 20.

    Returns:
        {"bollinger": {"upper","mid","lower"}, "keltner": {"upper","mid","lower"}, "squeeze": bool}.
    """
    sma = closes.rolling(period).mean().iloc[-1]
    std = closes.rolling(period).std().iloc[-1]
    bollinger = {"upper": round(sma + 2 * std, 4), "mid": round(sma, 4), "lower": round(sma - 2 * std, 4)}

    ema = closes.ewm(span=period, adjust=False).mean().iloc[-1]
    keltner_width = 1.5 * atr14
    keltner = {"upper": round(ema + keltner_width, 4), "mid": round(ema, 4), "lower": round(ema - keltner_width, 4)}

    squeeze = bool(bollinger["upper"] < keltner["upper"] and bollinger["lower"] > keltner["lower"])
    return {"bollinger": bollinger, "keltner": keltner, "squeeze": squeeze}


def compute_anchored_vwap(
    highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series,
    dates: pd.Series, anchor_date: str | None,
) -> float | None:
    """Volume-weighted average price from `anchor_date` forward.

    Args:
        highs, lows, closes, volumes: OHLCV columns, oldest first, same length as `dates`.
        dates: ISO date strings ("YYYY-MM-DD"), same index alignment as the OHLCV columns.
        anchor_date: The date to anchor from (inclusive), or None to skip.

    Returns:
        VWAP from the anchor date onward, or None if anchor_date is None or
        not present in `dates`.
    """
    if anchor_date is None or anchor_date not in set(dates):
        return None
    mask = dates >= anchor_date
    typical_price = (highs[mask] + lows[mask] + closes[mask]) / 3
    vol = volumes[mask]
    if vol.sum() == 0:
        return None
    return round(float((typical_price * vol).sum() / vol.sum()), 4)


def compute_volume_ratio(volumes: pd.Series, period: int = 20) -> float | None:
    """Latest volume divided by the trailing `period`-bar average volume.

    Args:
        volumes: Volume series, oldest first.
        period: Lookback window for the average, default 20.

    Returns:
        Ratio (>1.0 = above-average volume), or None if fewer than period+1 bars.
    """
    if len(volumes) < period + 1:
        return None
    avg = volumes.iloc[-(period + 1):-1].mean()
    if avg == 0:
        return None
    return round(float(volumes.iloc[-1] / avg), 3)


def compute_relative_strength(closes: pd.Series, benchmark_closes: pd.Series) -> dict:
    """Cumulative-return ratio vs. a benchmark, plus its 63-day slope.

    Args:
        closes: Ticker close prices, oldest first.
        benchmark_closes: Benchmark (e.g. SPY) close prices, same length/alignment.

    Returns:
        {"ratio": float, "slope63d": float}. Ratio > 1.0 means the ticker has
        outperformed the benchmark since the start of the supplied window;
        slope63d is the least-squares slope of the ratio series over its
        trailing 63 bars (positive = improving relative strength).
    """
    ticker_cum = closes / closes.iloc[0]
    benchmark_cum = benchmark_closes / benchmark_closes.iloc[0]
    ratio_series = (ticker_cum / benchmark_cum).dropna()
    ratio = float(ratio_series.iloc[-1])

    window = ratio_series.iloc[-63:]
    x = np.arange(len(window))
    if len(window) < 2 or np.var(x) == 0:
        slope = 0.0
    else:
        slope = float(np.cov(x, window.values, bias=True)[0, 1] / np.var(x))

    return {"ratio": round(ratio, 4), "slope63d": round(slope, 6)}


def compute_technical_snapshot(
    ticker: str, timeframe: str, period: str, benchmark: str, anchor_date: str | None,
) -> dict:
    """Primary orchestrator — one TechnicalSnapshot per ticker/timeframe.

    If `anchor_date` is not supplied, attempts to auto-detect one via
    `_default_earnings_anchor` (see that function's docstring for why this
    rarely resolves to a usable date today); if neither is available,
    anchoredVwap is None rather than guessed.

    Args:
        ticker: Ticker symbol.
        timeframe: "D" or "W".
        period: yfinance period string (e.g. "1y") passed to market_data.get_prices().
        benchmark: Benchmark ticker for relative strength (e.g. "SPY").
        anchor_date: ISO date string to anchor VWAP from, or None for auto-detection.

    Returns:
        Full TechnicalSnapshot dict — see docs/superpowers/specs/
        2026-07-05-fundamental-analyst-ta-design.md for the field-by-field shape.
    """
    interval = "1d" if timeframe == "D" else "1wk"
    prices = get_prices([ticker, benchmark], period=period, interval=interval)
    rows = prices.get(ticker, {}).get("data", [])
    benchmark_rows = prices.get(benchmark, {}).get("data", [])
    df = pd.DataFrame(rows)
    benchmark_df = pd.DataFrame(benchmark_rows)

    if df.empty:
        return {
            "ticker": ticker, "timeframe": timeframe, "asOf": None,
            "rsi14": None, "ema21": None, "ema50": None, "ema200": None,
            "macd": None, "adx14": None, "plusDI": None, "minusDI": None,
            "atr14": None, "bollinger": None, "keltner": None, "squeeze": None,
            "anchoredVwap": None, "volumeRatio20d": None,
            "relativeStrength": {"ratio": None, "slope63d": None},
        }

    if anchor_date is None:
        anchor_date = _default_earnings_anchor(ticker)

    atr14 = compute_atr(df["high"], df["low"], df["close"]) or 0.0
    adx_result = compute_adx(df["high"], df["low"], df["close"])

    # Align ticker and benchmark on calendar date (inner join) before computing
    # relative strength — a positional (RangeIndex) division would silently pair
    # up mismatched dates if the two series have different lengths/histories
    # (e.g. a recently-IPO'd ticker vs. a long-history benchmark).
    if not benchmark_df.empty:
        merged = df[["date", "close"]].merge(
            benchmark_df[["date", "close"]], on="date", suffixes=("", "_benchmark")
        )
        relative_strength = (
            compute_relative_strength(merged["close"], merged["close_benchmark"])
            if not merged.empty else {"ratio": None, "slope63d": None}
        )
    else:
        relative_strength = {"ratio": None, "slope63d": None}

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "asOf": df["date"].iloc[-1] if not df.empty else None,
        "rsi14": compute_rsi(df["close"]),
        "ema21": compute_ema(df["close"], 21),
        "ema50": compute_ema(df["close"], 50),
        "ema200": compute_ema(df["close"], 200),
        "macd": compute_macd(df["close"]),
        **adx_result,
        "atr14": atr14,
        **compute_bollinger_keltner_squeeze(df["close"], df["high"], df["low"], atr14),
        "anchoredVwap": compute_anchored_vwap(
            df["high"], df["low"], df["close"], df["volume"], df["date"], anchor_date
        ),
        "volumeRatio20d": compute_volume_ratio(df["volume"]),
        "relativeStrength": relative_strength,
    }


def _default_earnings_anchor(ticker: str) -> str | None:
    """Best-effort auto-anchor lookup for `ticker`, or None if unavailable.

    `get_earnings_calendar()` currently only returns upcoming/future earnings
    dates (by that module's own design — it exists to flag imminent binary
    events, not to look backward). As a result, this auto-anchor will rarely
    if ever resolve to a usable historical date today: it safely returns None
    in that case rather than fabricating one (see compute_anchored_vwap's None
    path). A future enhancement to earnings_calendar.py to expose past
    earnings dates would make this useful; until then, callers should pass
    `--anchor-date` explicitly for a working anchored VWAP.

    This walks entries defensively and returns None on any shape it doesn't
    recognize rather than raising, since a missing anchor is a normal,
    expected case. Calls the module-level `get_earnings_calendar` (imported
    at the top of this file, not locally) so tests can
    `patch("technicals.get_earnings_calendar", ...)` — a function-local
    import would make that patch target a name that doesn't exist in this
    module's namespace, and unittest.mock.patch would raise AttributeError
    instead of substituting the stub.
    """
    try:
        entries = get_earnings_calendar()
        for entry in entries:
            if getattr(entry, "ticker", None) == ticker:
                return getattr(entry, "earnings_date", None)
    except Exception:  # noqa: BLE001 - any failure here just means "no anchor available"
        return None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Local TA engine — full TechnicalSnapshot")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--timeframe", default="D", choices=["D", "W"])
    parser.add_argument("--period", default="1y")
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--anchor-date", default=None, help="YYYY-MM-DD, omit to auto-detect from earnings")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = compute_technical_snapshot(
        args.ticker, args.timeframe, args.period, args.benchmark, args.anchor_date
    )
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
