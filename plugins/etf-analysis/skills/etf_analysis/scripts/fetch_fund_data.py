#!/usr/bin/env python3
"""
fetch_fund_data.py — etf-analysis plugin

Fetches available market data for an ETF or closed-end fund via yfinance.
Outputs a structured JSON envelope to stdout for the ETF analysis skill to consume.

Usage:
    python3 fetch_fund_data.py DXYZ
    python3 fetch_fund_data.py KOID --holdings
    python3 fetch_fund_data.py HUMN --history 6mo
"""

import json
import argparse
from datetime import datetime, timezone


def fetch(ticker: str, include_holdings: bool = True, history_period: str = "6mo") -> dict:
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed", "ticker": ticker}

    tk = yf.Ticker(ticker)
    info = tk.info

    snapshot_keys = [
        "longName", "quoteType", "category", "totalAssets", "navPrice",
        "regularMarketPrice", "currency", "exchange", "expenseRatio",
        "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "averageVolume",
        "sharesOutstanding", "beta", "fundFamily", "legalType",
    ]
    snapshot = {k: info.get(k) for k in snapshot_keys if info.get(k) is not None}

    holdings = []
    if include_holdings:
        try:
            fd = tk.funds_data
            top = fd.top_holdings
            if top is not None and not top.empty:
                for sym, row in top.iterrows():
                    holdings.append({
                        "symbol": sym,
                        "name": str(row.get("Name", "")),
                        "holdingPct": round(float(row.get("Holding Percent") or 0) * 100, 2),
                    })
        except Exception:
            pass

    price_history = {}
    try:
        hist = tk.history(period=history_period)
        if not hist.empty:
            vals: list[float] = [float(v) for v in hist["Close"].dropna()]
            low, high, start, latest = min(vals), max(vals), vals[0], vals[-1]
            price_history = {
                "period": history_period,
                "low": round(low, 2),
                "high": round(high, 2),
                "start": round(start, 2),
                "latest": round(latest, 2),
                "changeP": round((latest / start - 1) * 100, 2) if start else 0,
            }
    except Exception:
        pass

    return {
        "ticker": ticker.upper(),
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "snapshot": snapshot,
        "topHoldings": holdings,
        "priceHistory": price_history,
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch fund data from yfinance")
    parser.add_argument("ticker", help="Fund ticker symbol")
    parser.add_argument("--holdings", action="store_true", default=True, help="Include top holdings")
    parser.add_argument("--history", default="6mo", help="History period (default: 6mo)")
    args = parser.parse_args()

    result = fetch(args.ticker, include_holdings=args.holdings, history_period=args.history)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
