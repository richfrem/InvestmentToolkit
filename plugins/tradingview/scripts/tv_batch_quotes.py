#!/usr/bin/env python3
"""
tv_batch_quotes.py — Batch price resolver: TradingView first, yfinance fallback.

Price source priority (in order):
  1. TradingView watchlist DOM via CDP — live prices including BOATS extended-hours feed.
     During BOATS session (8PM–4AM ET, Sun–Thu): reads TA-BOATS-Watchlist (BOATS:TICKER).
     All other hours: reads TA-Full Watchlist (NYSE/NASDAQ/extended).
  2. yfinance fast_info.last_price — reflects extended-hours prices when market is closed.
     Used when TradingView is not running (port 9222 unreachable) or ticker not in watchlist.

Usage:
    python3 tv_batch_quotes.py '["CRWV", "NVDA", "INTC"]'

Output (JSON):
    {
      "quotes": {
        "CRWV": { "price": 115.26, "changePercent": -6.07, "source": "tradingview" },
        "NVDA":  { "price": 205.19, "changePercent":  1.23, "source": "tradingview" },
        "INTC":  { "price":  22.14, "changePercent": -0.41, "source": "yfinance" }
      },
      "summary": {
        "total": 3,
        "tradingview": 2,
        "fallback": 1,
        "errors": 0,
        "boats_session": false
      }
    }
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here] + [here.parents[i] for i in range(9)]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")


def is_boats_active() -> bool:
    """Return True when Blue Ocean ATS (BOATS) session is live.

    BOATS hours: 8:00 PM – 4:00 AM ET, Sunday through Thursday only.
    Friday and Saturday nights have no BOATS session.
    """
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    hour = now.hour
    weekday = now.weekday()  # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6

    if hour >= 20:
        # Evening leg (8PM–midnight): valid Sun(6)–Thu(3)
        return weekday in (0, 1, 2, 3, 6)
    elif hour < 4:
        # Overnight leg (midnight–4AM): valid Mon(0)–Fri(4) early morning
        # (the previous night's session rolling over)
        return weekday in (0, 1, 2, 3, 4)
    return False


def _tv_watchlist_prices() -> dict[str, dict]:
    """Read live prices from the active TradingView watchlist via CDP.

    Opens TA-BOATS-Watchlist during BOATS hours, TA-Full Watchlist otherwise.
    Strips exchange prefixes (BOATS:, NASDAQ:) when building the lookup dict
    so callers can match against plain ticker symbols.

    Returns:
        Dict mapping plain ticker → {price, changePercent}.
        Empty dict if TradingView is unreachable or watchlist read fails.
    """
    sys.path.insert(0, str(_find_scripts_dir()))
    from tv_client import tv_call, is_tv_running  # type: ignore[import]

    if not is_tv_running():
        return {}

    boats = is_boats_active()
    watchlist_name = "TA-BOATS-Watchlist" if boats else "TA-Full Watchlist"

    try:
        open_res = tv_call("watchlist", "open", watchlist_name)
        if not open_res.get("success"):
            # Fallback: try the other watchlist
            alt = "TA-Full Watchlist" if boats else "TA-BOATS-Watchlist"
            tv_call("watchlist", "open", alt)

        get_res = tv_call("watchlist", "get")
        if not get_res.get("success"):
            return {}

        prices: dict[str, dict] = {}
        for item in get_res.get("items", []):
            raw_sym = item.get("symbol", "")
            # Strip exchange prefix: "BOATS:NVDA" → "NVDA", "NASDAQ:AAPL" → "AAPL"
            sym = raw_sym.split(":")[-1].upper() if ":" in raw_sym else raw_sym.upper()
            price = item.get("price", 0.0)
            change_pct = item.get("changePercent", 0.0)
            if sym and price:
                prices[sym] = {"price": price, "changePercent": change_pct}
        return prices

    except Exception:
        return {}


def _yf_fast_quote(ticker: str) -> Optional[dict]:
    """Fetch single-ticker quote via yfinance fast_info (extended-hours aware).

    Args:
        ticker: Plain ticker symbol (no exchange prefix).

    Returns:
        Dict with price, changePercent, or None on failure.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        fi = t.fast_info
        price = getattr(fi, "last_price", None)
        prev = getattr(fi, "previous_close", None)
        if not price or not prev or prev <= 0:
            return None
        change_pct = round((price - prev) / prev * 100, 4)
        return {"price": round(price, 4), "changePercent": change_pct}
    except Exception:
        return None


def batch_quotes(tickers: list[str]) -> dict:
    """Resolve prices for multiple tickers: TradingView first, yfinance fallback.

    Args:
        tickers: List of plain ticker symbols (no exchange prefix).

    Returns:
        Dict with 'quotes', 'errors', and 'summary' keys.
    """
    boats = is_boats_active()
    tv_prices = _tv_watchlist_prices()

    quotes: dict[str, dict] = {}
    errors: dict[str, str] = {}
    tv_count = 0
    yf_tickers: list[str] = []

    for t in tickers:
        if t in tv_prices:
            quotes[t] = {**tv_prices[t], "source": "tradingview"}
            tv_count += 1
        else:
            yf_tickers.append(t)

    # Parallel yfinance fallback for tickers not in TV watchlist
    if yf_tickers:
        with ThreadPoolExecutor(max_workers=min(len(yf_tickers), 8)) as pool:
            futures = {pool.submit(_yf_fast_quote, t): t for t in yf_tickers}
            for future in as_completed(futures, timeout=30):
                sym = futures[future]
                try:
                    result = future.result()
                    if result:
                        quotes[sym] = {**result, "source": "yfinance"}
                    else:
                        errors[sym] = "no price data"
                except Exception as e:
                    errors[sym] = str(e)

    return {
        "quotes": quotes,
        "errors": errors,
        "summary": {
            "total": len(tickers),
            "tradingview": tv_count,
            "fallback": len(quotes) - tv_count,
            "errors": len(errors),
            "boats_session": boats,
        },
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Batch price resolver — TV first, yfinance fallback.")
    parser.add_argument("tickers", help='JSON array e.g. \'["NVDA","AAPL"]\'')
    args = parser.parse_args()
    try:
        tickers = json.loads(args.tickers)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)
    if not isinstance(tickers, list):
        print(json.dumps({"error": "Input must be a JSON array"}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(batch_quotes(tickers), indent=2))


if __name__ == "__main__":
    main()
