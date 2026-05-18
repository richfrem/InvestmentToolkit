#!/usr/bin/env python3
"""
tv_batch_quotes.py - Get real-time quotes for a list of tickers via yfinance bulk download.

NOTE: TradingView CDP reads only the *active chart* symbol — it cannot batch-query multiple
tickers without significant delay. Therefore, this script exclusively uses yfinance for batch
operations by design. The summary output still includes `"tradingview": 0` to maintain the
API contract with existing consumers. Use tv_quote.py for a single ticker when that ticker
is currently displayed on the active TradingView chart.

Usage:
    python3 tv_batch_quotes.py '["CRWV", "NVDA", "INTC"]'

Output (JSON):
    {
      "quotes": {
        "CRWV": { "price": 115.26, "changePercent": -6.07, "source": "yfinance" },
        "NVDA":  { "price": 497.32, "changePercent":  1.23, "source": "yfinance" }
      },
      "summary": {
        "total": 2,
        "tradingview": 0,
        "fallback": 2,
        "errors": 0
      }
    }
"""

import sys
import json
import argparse
from pathlib import Path


def batch_quotes(tickers: list[str]) -> dict:
    """Fetch quotes for multiple tickers via yfinance bulk download.

    Args:
        tickers: List of ticker symbols.

    Returns:
        Dict with 'quotes', 'errors', and 'summary' keys.
    """
    import yfinance as yf

    quotes: dict = {}
    errors: dict = {}

    # yfinance download fetches all tickers in one HTTP round-trip
    data = yf.download(tickers, period="2d", interval="1d",
                       progress=False, auto_adjust=True)

    close_df = data["Close"]
    closes = close_df.iloc[-1] if len(close_df) >= 1 else {}
    prev_closes = close_df.iloc[-2] if len(close_df) >= 2 else {}

    for ticker in tickers:
        try:
            price = float(closes[ticker])  # type: ignore[index]
            prev_val = prev_closes.get(ticker) if hasattr(prev_closes, "get") else None
            prev = float(prev_val) if prev_val is not None else price
            change = round(price - prev, 4)
            change_pct = round((change / prev) * 100, 4) if prev else 0.0
            quotes[ticker] = {
                "price": round(price, 4),
                "change": change,
                "changePercent": change_pct,
                "volume": 0,
                "source": "yfinance",
            }
        except Exception as e:
            errors[ticker] = str(e)

    return {
        "quotes": quotes,
        "errors": errors,
        "summary": {
            "total": len(tickers),
            "tradingview": 0,
            "fallback": len(quotes),
            "errors": len(errors),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Get real-time quotes for a list of tickers."
    )
    parser.add_argument(
        "tickers",
        help='JSON array of ticker symbols, e.g. \'["CRWV","NVDA"]\'',
    )
    args = parser.parse_args()

    try:
        tickers = json.loads(args.tickers)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    if not isinstance(tickers, list):
        print(json.dumps({"error": "Input must be a JSON array"}), file=sys.stderr)
        sys.exit(1)

    result = batch_quotes(tickers)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
