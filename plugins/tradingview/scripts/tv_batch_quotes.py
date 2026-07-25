#!/usr/bin/env python3
"""
tv_batch_quotes.py — Batch price resolver: TradingView first, yfinance fallback.

Price source priority (in order):
  1. TradingView watchlist DOM via CDP — reads the live "TV-Full Watchlist"
     (real, current TradingView watchlist name; TradingView charts now natively
     support 24h quoting, so there is no separate overnight/BOATS watchlist).
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
        "errors": 0
      }
    }
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

TV_WATCHLIST_NAME = "TV-Full Watchlist"


def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")


def _tv_watchlist_prices() -> dict[str, dict]:
    """Read live prices from the active TradingView watchlist via CDP.

    Opens TV_WATCHLIST_NAME ("TV-Full Watchlist") — the single real, current
    TradingView watchlist used for all-hours pricing (no BOATS/overnight split;
    TradingView charts now natively support 24h quoting).

    Returns:
        Dict mapping plain ticker → {price, changePercent}.
        Empty dict if TradingView is unreachable or watchlist read fails.
    """
    sys.path.insert(0, str(_find_scripts_dir()))
    from tv_client import tv_call, is_tv_running  # type: ignore[import]

    if not is_tv_running():
        return {}

    try:
        open_res = tv_call("watchlist", "open", TV_WATCHLIST_NAME)
        if not open_res.get("success"):
            return {}

        get_res = tv_call("watchlist", "get")
        if not get_res.get("success"):
            return {}

        prices: dict[str, dict] = {}
        for item in get_res.get("items", []):
            raw_sym = item.get("symbol", "")
            # Strip exchange prefix if present: "NASDAQ:AAPL" → "AAPL"
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
        yf_ticker = ticker
        if ".U.TO" in ticker:
            yf_ticker = ticker.replace(".U.TO", "-U.TO")
        t = yf.Ticker(yf_ticker)
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
