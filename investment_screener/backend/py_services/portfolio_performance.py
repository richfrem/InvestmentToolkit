#!/usr/bin/env python3
"""
portfolio_performance.py - Python utility script.

Purpose:
    Calculates aggregate portfolio performance over standard horizons (1d, 1w, 1m).
    Downloads batched historical data via yfinance and uses the most recent close as the "current" price 
    baseline to ensure accuracy independent of brokerage sync staleness.

Layer:
    Backend / Python Services

Usage Examples:
    python3 portfolio_performance.py investment_screener/backend/data/portfolio.json

Key Functions (Index):
    - safe_float()
    - load_portfolio_data()
    - fetch_history_dataframe()
    - compute_performance()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import json
import sys
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import pandas as pd
import yfinance as yf


# External comment: Safely cast value to float handling NaN and None cases
def safe_float(val: Any) -> float:
    """
    Utility to handle NaN/None values from financial data frames.
    """
    if val is None:
        return 0.0
    try:
        f = float(val)
        return 0.0 if math.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0


# External comment: Load portfolio JSON data and extract equity positions and cash values
def load_portfolio_data(portfolio_path: str) -> Tuple[float, List[str], Dict[str, float]]:
    """
    Reads holdings, calculates total cash, and returns (cash_value, tickers, shares_map).
    """
    with open(portfolio_path) as f:
        raw = json.load(f)
    portfolio = raw if isinstance(raw, list) else raw.get("holdings", [])

    equity_positions = [
        p for p in portfolio
        if p.get("sector") != "CASH" and p.get("symbol") != "USD_CASH"
    ]
    cash_value = sum(
        p.get("shares", 0) * p.get("price", 1.0)
        for p in portfolio
        if p.get("sector") == "CASH" or p.get("symbol") == "USD_CASH"
    )

    tickers = [p["symbol"] for p in equity_positions]
    shares_map = {p["symbol"]: p["shares"] for p in equity_positions}

    return cash_value, tickers, shares_map


# External comment: Fetches and normalizes yfinance historical pricing dataframe
def fetch_history_dataframe(tickers: List[str]) -> pd.DataFrame:
    """
    Downloads historical close prices and normalizes index timezone.
    """
    # Fetch 35 calendar days of history in one batch call
    raw = yf.download(tickers, period="35d", auto_adjust=True, progress=False)

    if raw is None or raw.empty:
        return pd.DataFrame()

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

    return close


# External comment: Calculates dollar and percentage return changes over standard periods
def compute_performance(
    close: pd.DataFrame,
    shares_map: Dict[str, float],
    cash_value: float,
    tickers: List[str],
    now: datetime,
) -> Dict[str, Any]:
    """
    Pure computation over an already-fetched close-price DataFrame with forward-fill.
    """
    close = close.ffill()

    current_row = close.iloc[-1]
    current_equity = sum(
        shares_map[t] * safe_float(current_row.get(t) if hasattr(current_row, "get") else current_row[t])
        for t in tickers
    )
    current_total = current_equity + cash_value

    periods = {
        "1d": now - timedelta(days=1),
        "1w": now - timedelta(days=7),
        "1m": now - timedelta(days=30),
    }

    result: Dict[str, Any] = {}
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

    return result


# External comment: Entry point execution orchestrator
def main() -> None:
    """
    CLI orchestrator that filters positions, fetches history, and runs performance calculations.
    """
    if len(sys.argv) < 2:
        print(json.dumps({"error": "portfolio path required"}))
        sys.exit(1)

    cash_value, tickers, shares_map = load_portfolio_data(sys.argv[1])

    if not tickers:
        fallback = cash_value
        result = {p: {"change": 0.0, "changePct": 0.0, "historicalValue": fallback, "currentValue": fallback}
                  for p in ("1d", "1w", "1m")}
        print(json.dumps(result))
        return

    close = fetch_history_dataframe(tickers)
    if close.empty:
        print(json.dumps({"error": "no price data returned from yfinance"}))
        return

    result = compute_performance(close, shares_map, cash_value, tickers, datetime.now())
    print(json.dumps(result))


if __name__ == "__main__":
    main()
