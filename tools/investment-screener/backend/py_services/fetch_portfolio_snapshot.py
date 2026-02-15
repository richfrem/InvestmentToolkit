#!/usr/bin/env python3
"""
fetch_portfolio_snapshot.py
===========================

Purpose:
    Fetches current market data (Price, Market Cap, PE, etc.) for a list of tickers.
    Used by the Thesis Balancer to get fresh data for health checks.
    Uses generic yfinance for batch efficiency where possible.

Layer: Tools / Investment-Screener

Usage Examples:
    python tools/investment-screener/backend/py_services/fetch_portfolio_snapshot.py '["AAPL", "MSFT", "INTC"]'

CLI Arguments:
    tickers_json : JSON string list of tickers

Returns:
    JSON map: { ticker: { price, marketCap, pe, beta, fiftyTwoWeekHigh, fiftyTwoWeekLow, ... } }
"""

import sys
import json
import logging
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_snapshot(tickers):
    """
    Fetches snapshot data for a list of tickers.
    """
    if not tickers:
        return {}

    logger.info(f"Fetching data for {len(tickers)} tickers: {tickers}")
    
    # yfinance.Tickers is more efficient than looping Ticker()
    tickers_str = " ".join(tickers)
    data = yf.Tickers(tickers_str)
    
    results = {}
    
    for ticker in tickers:
        try:
            # Accessing .info triggers a fetch for that ticker if not already cached
            # Note: yf.Tickers might still fetch serially under the hood dependent on version, 
            # but it is the standard way to group them.
            # Efficient batching of .info is notoriously tricky in yfinance as it targets 'quoteSummary' endpoint.
            # We will use this loop, but handle errors gracefully.
            
            info = data.tickers[ticker].info
            
            results[ticker] = {
                "price": info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
                "marketCap": info.get("marketCap"),
                "pe": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "beta": info.get("beta"),
                "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
                "dividendYield": info.get("dividendYield"),
                "sector": info.get("sector"),
                "industry": info.get("industry")
            }
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            results[ticker] = {
                "error": str(e),
                "price": 0.0
            }
            
    return results

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No tickers provided"}))
        sys.exit(1)

    try:
        tickers = json.loads(sys.argv[1])
        if not isinstance(tickers, list):
             raise ValueError("Input must be a JSON list of strings")
    except Exception as e:
        print(json.dumps({"error": f"Invalid input: {str(e)}"}))
        sys.exit(1)

    try:
        snapshot = fetch_snapshot(tickers)
        print(json.dumps(snapshot, indent=2))
    except Exception as e:
        print(json.dumps({"error": f"Execution failed: {str(e)}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
