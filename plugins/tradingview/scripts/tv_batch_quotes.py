#!/usr/bin/env python3
"""
tv_batch_quotes.py - Get real-time quotes for a list of tickers.

Usage:
    python3 tv_batch_quotes.py '["CRWV", "NVDA", "INTC"]'

Concurrency: ThreadPoolExecutor(max_workers=5) — parallelises per-ticker calls.

Output (JSON):
    {
      "quotes": {
        "CRWV": { "price": 115.26, "changePercent": -6.07, "source": "tradingview" },
        "NVDA":  { "price": 497.32, "changePercent":  1.23, "source": "tradingview" }
      },
      "summary": {
        "total": 2,
        "tradingview": 2,
        "fallback": 0,
        "errors": 0
      }
    }
"""

import sys
import json
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
from tv_quote import get_quote  # type: ignore[import-not-found]


def batch_quotes(tickers: list[str]) -> dict:
    """Fetch quotes for multiple tickers in parallel."""
    quotes = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ticker = {
            executor.submit(get_quote, ticker): ticker for ticker in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                quotes[ticker] = {
                    "price": result.get("price", 0.0),
                    "change": result.get("change", 0.0),
                    "changePercent": result.get("changePercent", 0.0),
                    "volume": result.get("volume", 0),
                    "source": result.get("source", "unknown"),
                }
            except Exception as e:
                errors[ticker] = str(e)

    tv_count = sum(1 for q in quotes.values() if q["source"] == "tradingview")
    fb_count = sum(1 for q in quotes.values() if q["source"] != "tradingview")

    return {
        "quotes": quotes,
        "errors": errors,
        "summary": {
            "total": len(tickers),
            "tradingview": tv_count,
            "fallback": fb_count,
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
