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


def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here] + [here.parents[i] for i in range(9)]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")


def batch_quotes(tickers: list[str]) -> dict:
    """Fetch quotes for multiple tickers. Uses TradingView for the active chart symbol,
    and yfinance for the rest.

    Args:
        tickers: List of ticker symbols.

    Returns:
        Dict with 'quotes', 'errors', and 'summary' keys.
    """
    import yfinance as yf
    
    sys.path.insert(0, str(_find_scripts_dir()))
    from tv_client import tv_call, is_tv_running

    quotes: dict = {}
    errors: dict = {}
    active_ticker = None
    tv_quote = None
    tv_count = 0

    if is_tv_running():
        try:
            status_res = tv_call("status")
            if status_res.get("success") and status_res.get("chart_symbol"):
                active_ticker = status_res["chart_symbol"].split(":")[-1].upper()
                # Remove alias mappings if applicable (e.g. PSU-U.TO / PSU.U.TO)
                if active_ticker == "PSU.U.TO" and "PSU-U.TO" in tickers:
                    active_ticker = "PSU-U.TO"
                if active_ticker in tickers:
                    tv_raw = tv_call("quote", active_ticker)
                    if tv_raw.get("success"):
                        tv_quote = {
                            "price": tv_raw.get("price") or tv_raw.get("header_price") or 0.0,
                            "change": tv_raw.get("change", 0.0),
                            "changePercent": tv_raw.get("changePercent", 0.0),
                            "volume": tv_raw.get("volume", 0),
                            "source": "tradingview",
                        }
                        quotes[active_ticker] = tv_quote
                        tv_count = 1
        except Exception:
            pass

    yf_tickers = [t for t in tickers if t != active_ticker] if tv_quote else tickers

    if yf_tickers:
        try:
            data = yf.download(yf_tickers, period="2d", interval="1d",
                               progress=False, auto_adjust=True)

            close_df = data["Close"]
            closes = close_df.iloc[-1] if len(close_df) >= 1 else {}
            prev_closes = close_df.iloc[-2] if len(close_df) >= 2 else {}

            for ticker in yf_tickers:
                try:
                    price = float(closes[ticker]) if len(yf_tickers) > 1 else float(close_df.iloc[-1])
                    prev_val = prev_closes[ticker] if len(yf_tickers) > 1 else float(close_df.iloc[-2]) if len(close_df) >= 2 else None
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
        except Exception as e:
            for ticker in yf_tickers:
                errors[ticker] = f"Bulk yfinance failed: {e}"

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
