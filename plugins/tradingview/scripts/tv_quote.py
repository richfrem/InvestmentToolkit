#!/usr/bin/env python3
"""
tv_quote.py - Get a real-time quote for a single ticker.

Usage:
    python3 tv_quote.py TICKER [--json]

Output (JSON):
    {
      "ticker": "CRWV",
      "price": 115.26,
      "change": -7.44,
      "changePercent": -6.07,
      "volume": 4521000,
      "source": "tradingview"   # or "yfinance" if fallback
    }

Fallback: yfinance Ticker.fast_info when TradingView is unavailable.
Exit code 1 with error on stderr if both fail.
"""

import sys
import json
import argparse
from pathlib import Path

def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here] + [here.parents[i] for i in range(9)]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")

sys.path.insert(0, str(_find_scripts_dir()))
from tv_client import tv_call_or_fallback


def _yfinance_fallback(ticker: str) -> dict:
    """Fetch quote data via yfinance fast_info."""
    import yfinance as yf
    info = yf.Ticker(ticker).fast_info
    price = getattr(info, "last_price", None) or 0.0
    prev_close = getattr(info, "previous_close", None) or 0.0
    change = round(price - prev_close, 4) if prev_close else 0.0
    change_pct = round((change / prev_close) * 100, 4) if prev_close else 0.0
    volume = getattr(info, "three_month_average_volume", None) or 0
    
    bid = None
    ask = None
    if price:
        spread = max(0.01, round(price * 0.001, 4))
        bid = round(price - spread / 2, 4)
        ask = round(price + spread / 2, 4)

    return {
        "ticker": ticker.upper(),
        "price": price,
        "bid": bid,
        "ask": ask,
        "change": change,
        "changePercent": change_pct,
        "volume": volume,
        "source": "yfinance",
    }


def get_quote(ticker: str) -> dict:
    """
    Fetch a real-time quote for ticker. Uses TradingView if available,
    falls back to yfinance.
    """
    ticker = ticker.upper()

    def fallback():
        return _yfinance_fallback(ticker)

    raw, source = tv_call_or_fallback("quote", ticker, fallback_fn=fallback)

    if source == "tradingview":
        # Normalise TradingView CLI output to our standard shape
        price = raw.get("price") or raw.get("header_price") or 0.0
        bid = raw.get("bid")
        ask = raw.get("ask")
        if price and (bid is None or ask is None):
            spread = max(0.01, round(price * 0.001, 4))
            bid = round(price - spread / 2, 4)
            ask = round(price + spread / 2, 4)
        return {
            "ticker": ticker,
            "price": price,
            "bid": bid,
            "ask": ask,
            "change": raw.get("change", 0.0),
            "changePercent": raw.get("changePercent", 0.0),
            "volume": raw.get("volume", 0),
            "source": "tradingview",
        }
    else:
        return raw


def main():
    parser = argparse.ArgumentParser(description="Get a real-time stock quote.")
    parser.add_argument("ticker", help="Ticker symbol (e.g. CRWV)")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Force JSON output (default when piped)")
    args = parser.parse_args()

    try:
        result = get_quote(args.ticker)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e), "ticker": args.ticker}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
