#!/usr/bin/env python3
"""
Calculate portfolio performance over 1d, 1w, 1m periods using yfinance.
Uses the most recent yfinance close as "current" for accuracy regardless of
how stale portfolio.json prices are.

Usage: python3 portfolio_performance.py <portfolio_json_path>
Output: JSON { "1d": { change, changePct, historicalValue, currentValue }, "1w": ..., "1m": ... }
"""
import json
import sys
import math
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        f = float(val)
        return 0.0 if math.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "portfolio path required"}))
        sys.exit(1)

    with open(sys.argv[1]) as f:
        portfolio = json.load(f)

    equity_positions = [
        p for p in portfolio
        if p.get("sector") != "CASH" and p.get("symbol") != "USD_CASH"
    ]
    cash_value = sum(
        p.get("shares", 0) * p.get("price", 1.0)
        for p in portfolio
        if p.get("sector") == "CASH" or p.get("symbol") == "USD_CASH"
    )

    if not equity_positions:
        fallback = cash_value
        result = {p: {"change": 0.0, "changePct": 0.0, "historicalValue": fallback, "currentValue": fallback}
                  for p in ("1d", "1w", "1m")}
        print(json.dumps(result))
        return

    tickers = [p["symbol"] for p in equity_positions]
    shares_map = {p["symbol"]: p["shares"] for p in equity_positions}

    # Fetch 35 calendar days of history in one batch call
    raw = yf.download(tickers, period="35d", auto_adjust=True, progress=False)

    if raw is None or raw.empty:
        print(json.dumps({"error": "no price data returned from yfinance"}))
        return

    # Normalise to a ticker-keyed Close DataFrame
    if isinstance(raw.columns, pd.MultiIndex):
        close: pd.DataFrame = raw["Close"]  # type: ignore[assignment]
    elif len(tickers) == 1:
        close = raw[["Close"]].rename(columns={"Close": tickers[0]})  # type: ignore[arg-type]
    else:
        close = raw

    # Strip timezone so comparisons work with naive datetime
    if hasattr(close.index, "tz") and getattr(close.index, "tz", None) is not None:
        close.index = close.index.tz_localize(None)  # type: ignore[assignment]

    if close.empty:
        print(json.dumps({"error": "no price data returned from yfinance"}))
        return

    # Use the last yfinance row as the "current" value (more accurate than cached portfolio.json)
    current_row = close.iloc[-1]
    current_equity = sum(
        shares_map[t] * safe_float(current_row.get(t) if hasattr(current_row, "get") else current_row[t])
        for t in tickers
    )
    current_total = current_equity + cash_value

    now = datetime.now()
    periods = {
        "1d": now - timedelta(days=1),
        "1w": now - timedelta(days=7),
        "1m": now - timedelta(days=30),
    }

    result: dict = {}
    for label, ref_date in periods.items():
        try:
            past_dates = close.index[close.index <= pd.Timestamp(ref_date)]
            if len(past_dates) == 0:
                result[label] = None
                continue

            past_row = close.loc[past_dates[-1]]
            past_equity = sum(
                shares_map[t] * safe_float(past_row.get(t) if hasattr(past_row, "get") else past_row[t])
                for t in tickers
            )
            past_total = past_equity + cash_value
            change = current_total - past_total
            change_pct = (change / past_total * 100) if past_total > 0 else 0.0

            result[label] = {
                "change": round(change, 2),
                "changePct": round(change_pct, 4),
                "historicalValue": round(past_total, 2),
                "currentValue": round(current_total, 2),
            }
        except Exception as e:
            result[label] = {"error": str(e)}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
