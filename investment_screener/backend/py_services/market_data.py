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
