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
    absent from the response, not present-and-wrong. See
    .agent/rules/no-silent-nan-to-zero.md.

Layer: Backend / Python Services / Data Layer
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cache  # noqa: E402
from cache import cache_get, cache_set  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / ".." / "data" / "cache"


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format.

    Returns:
        ISO 8601 datetime string (UTC).
    """
    return datetime.now(timezone.utc).isoformat()


def get_prices(tickers: list, period: str, interval: str = "1d") -> dict:
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
    # Sync cache module's CACHE_DIR with ours (supports monkeypatching in tests)
    cache.CACHE_DIR = CACHE_DIR

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
            rows.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(row.get("Open", 0.0)),
                "high": float(row.get("High", 0.0)),
                "low": float(row.get("Low", 0.0)),
                "close": float(row.get("Close", 0.0)),
                "volume": int(row.get("Volume", 0)),
            })
        entry = {"data": rows, "asOf": _now_iso()}
        cache_set(f"{t}_{period}_{interval}", "ohlcv", entry)
        result[t] = {**entry, "source": "yfinance"}

    return result
