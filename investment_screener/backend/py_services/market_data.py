"""
market_data.py (Python Service)
=====================================

Purpose:
    Single provider-abstracted interface for prices, quotes, analyst estimates,
    and fundamentals. Every returned field is source-tagged {"value","source","asOf"}
    (or, for get_prices/get_quote/get_estimates, the whole response is tagged since
    there is only ever one real provider per call). Only get_fundamentals() has a
    real multi-provider waterfall (EDGAR primary, yfinance supplement) — see
    docs/superpowers/specs/2026-07-02-data-layer-design.md.

    Never returns a zeroed/defaulted value for missing data — a missing field is
    absent from the response, not present-and-wrong. This applies equally to
    partial/NaN rows from upstream providers: a NaN value must never be
    silently coerced to zero, and must never crash the whole batch request
    either — the affected row is simply omitted for that ticker.

Layer: Backend / Python Services / Data Layer
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cache import cache_get, cache_set  # noqa: E402


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format.

    Returns:
        ISO 8601 datetime string (UTC).
    """
    return datetime.now(timezone.utc).isoformat()


def get_prices(tickers: list[str], period: str, interval: str = "1d") -> dict[str, dict]:
    """Fetch OHLCV price data for one or more tickers.

    Attempts to retrieve prices from cache first. For any ticker not in cache,
    fetches from yfinance, caches the result, and returns it tagged with the source.

    Args:
        tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"]).
        period: Time period for historical data (e.g., "5d", "1mo", "1y").
        interval: Candle interval (default "1d" for daily).

    Returns:
        Dict mapping ticker to result dict. Each result has:
            - "data": List of OHLCV dicts with keys date, open, high, low, close, volume.
            - "source": "yfinance" or "cache".
            - "asOf": ISO 8601 timestamp of fetch/cache.
    """
    result = {}
    to_fetch = []
    for t in tickers:
        cached = cache_get(f"{t}_{period}_{interval}", "ohlcv")
        if cached is not None:
            result[t] = {**cached, "source": "cache"}
        else:
            to_fetch.append(t)

    if not to_fetch:
        return result

    raw = yf.download(to_fetch, period=period, interval=interval, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return result

    for t in to_fetch:
        try:
            if isinstance(raw.columns, type(raw.columns)) and hasattr(raw.columns, "levels"):
                sub = raw.xs(t, axis=1, level=1)
            else:
                sub = raw
        except KeyError:
            continue
        rows = []
        for idx, row in sub.iterrows():
            o, hi, lo, c, v = (
                row.get("Open"), row.get("High"), row.get("Low"),
                row.get("Close"), row.get("Volume"),
            )
            # Misaligned trading calendars (e.g. a TSX ticker alongside a NASDAQ
            # ticker) leave real NaN values — not missing keys — for the ticker
            # that didn't trade that day. Skip the row for this ticker rather
            # than crash (int(NaN) raises ValueError) or fabricate a zero.
            if any(pd.isna(field) for field in (o, hi, lo, c, v)):
                continue
            rows.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(o),
                "high": float(hi),
                "low": float(lo),
                "close": float(c),
                "volume": int(v),
            })
        entry = {"data": rows, "asOf": _now_iso()}
        cache_set(f"{t}_{period}_{interval}", "ohlcv", entry)
        result[t] = {**entry, "source": "yfinance"}

    return result


def get_quote(tickers: list[str]) -> dict[str, dict]:
    """Fetch the latest price quote for one or more tickers.

    Attempts to retrieve each quote from cache first (15-minute TTL, see
    cache.CACHE_TTL_SECONDS["quote"]). For any ticker not in cache, fetches
    the current price from yfinance's fast_info, caches the result, and
    returns it tagged with the source.

    Note: this is yfinance-only. Per documented pitfall #7, TV CDP's `quote`
    command reads only the active chart symbol regardless of the ticker
    requested, so it cannot be used for batch quoting without silently
    returning wrong-ticker data. A TV-CDP single-ticker quote path is
    intentionally out of scope here.

    Args:
        tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"]).

    Returns:
        Dict mapping ticker to result dict. Each result has:
            - "price": Latest price as a float.
            - "source": "yfinance" or "cache".
            - "asOf": ISO 8601 timestamp of fetch/cache.
    """
    result = {}
    for t in tickers:
        cached = cache_get(t, "quote")
        if cached is not None:
            result[t] = {**cached, "source": "cache"}
            continue
        # A single bad/delisted ticker (missing "lastPrice", or any other
        # response-shape drift from yfinance) must not raise out of this
        # loop and kill the whole batch — skip just this ticker and keep
        # processing the rest, mirroring the per-row skip in get_prices().
        try:
            info = yf.Ticker(t).fast_info
            price = info.get("lastPrice") if hasattr(info, "get") else info["lastPrice"]
            price = float(price)
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
        entry = {"price": price, "asOf": _now_iso()}
        cache_set(t, "quote", entry)
        result[t] = {**entry, "source": "yfinance"}
    return result


def _extract_avg_estimate(df, row_label: str):
    """Safely pull a float 'avg' value for one row out of an estimates table.

    Guards against every way an analyst-estimates DataFrame can be missing or
    malformed: the whole object being None, not a DataFrame, empty, lacking
    the requested row or the 'avg' column, or containing a NaN in that cell.
    None of these are errors worth raising for — they all mean "no estimate
    available for this field" and must degrade to None, never 0.0.

    Args:
        df: The (possibly None/empty/malformed) estimates DataFrame.
        row_label: Row index label to read (e.g. "0y", "+1y").

    Returns:
        The estimate as a float, or None if unavailable in any way.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if row_label not in df.index or "avg" not in df.columns:
        return None
    try:
        value = df.loc[row_label, "avg"]
    except (KeyError, TypeError):
        return None
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_estimates(ticker: str) -> dict:
    """Fetch analyst forward revenue estimates for the current and next fiscal year.

    Attempts to retrieve the estimate from cache first (24h TTL, see
    cache.CACHE_TTL_SECONDS["fundamentals"]). On a cache miss, fetches
    yfinance's revenue_estimate table, extracts the "0y" (current fiscal
    year) and "+1y" (next fiscal year) analyst-consensus averages, caches
    the result, and returns it tagged with the source.

    Never raises on missing or malformed upstream data: a ticker with no
    analyst coverage, a revenue_estimate access that itself throws, an
    empty/None table, a missing row, or a NaN 'avg' cell all degrade to a
    None value for the affected field rather than crashing the caller or
    silently returning a zeroed estimate.

    Args:
        ticker: Ticker symbol (e.g., "PLTR").

    Returns:
        Dict with:
            - "y1RevEstimate": float|None current fiscal year revenue estimate.
            - "y2RevEstimate": float|None next fiscal year revenue estimate.
            - "source": "yfinance" or "cache".
            - "asOf": ISO 8601 timestamp of fetch/cache.
    """
    cached = cache_get(ticker, "fundamentals")
    if cached is not None and "y1RevEstimate" in cached:
        return {**cached, "source": "cache"}

    # yfinance's revenue_estimate property can itself raise (network errors,
    # upstream parsing failures, etc.) for a single ticker — that must not
    # propagate and kill the caller, mirroring the per-ticker guard in
    # get_quote().
    try:
        df = yf.Ticker(ticker).revenue_estimate
    except Exception:  # noqa: BLE001 - yfinance's failure modes here are unbounded
        # (network errors, upstream JSON/schema drift, etc.); any of them means
        # "no estimate available", never a reason to crash the caller.
        df = None

    y1 = _extract_avg_estimate(df, "0y")
    y2 = _extract_avg_estimate(df, "+1y")

    entry = {"y1RevEstimate": y1, "y2RevEstimate": y2, "asOf": _now_iso()}
    cache_set(ticker, "fundamentals", entry)
    return {**entry, "source": "yfinance"}
