#!/usr/bin/env python3
"""
fetch_portfolio_heatmap.py
=====================================

Purpose:
    Fetches portfolio data for treemap visualization.
    Calculates sector and industry allocations based on shares and current prices.

Layer: Tools / Investment-Screener

Usage Examples:
    python tools/investment-screener/backend/py_services/fetch_portfolio_heatmap.py '[{"symbol": "AAPL", "shares": 100}]'

CLI Arguments:
    portfolio_json  : JSON string representing the portfolio items

Key Functions:
    - get_stock_info()        : Safely retrieves ticker data from Yahoo Finance.
    - calculate_allocation()   : Computes position value and change percentages.
    - fetch_portfolio_data()  : Orchestrates the full data collection process.

Related:
    - fetch_financials.py
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import yfinance as yf

# Sector/industry overrides for stocks Yahoo doesn't classify correctly
SECTOR_OVERRIDES = {
    "HUMN": {"sector": "Technology", "industry": "Software - Application"},
    "KOID": {"sector": "Technology", "industry": "Software - Application"},
    "IBIT": {"sector": "Cryptocurrency", "industry": "Bitcoin ETF"},
    "SOLZ": {"sector": "Cryptocurrency", "industry": "Crypto Assets"},
    "ETHA": {"sector": "Cryptocurrency", "industry": "Ethereum ETF"},
    "COIN": {"sector": "Cryptocurrency", "industry": "Crypto Exchange"},
}


def get_position_metadata(item: Any) -> Dict[str, Any]:
    """
    Normalizes input portfolio items into a standard structure.

    Args:
        item: A string symbol or a dictionary with symbol/shares/overrides.

    Returns:
        Dictionary with normalized symbol, shares, and optional sector/industry overrides.
    """
    if isinstance(item, str):
        return {
            "symbol": item,
            "shares": 1,
            "sector": None,
            "industry": None
        }

    return {
        "symbol": item.get("symbol", ""),
        "shares": item.get("shares", 1),
        "sector": item.get("sector"),
        "industry": item.get("industry")
    }


def resolve_classification(symbol: str, info: Dict[str, Any], overrides: Dict[str, Any]) -> tuple:
    """
    Determines the sector and industry for a stock based on hierarchy of overrides.

    Args:
        symbol: The stock ticker symbol.
        info: Raw info dictionary from yfinance.
        overrides: Dictionary containing per-item overrides.

    Returns:
        tuple: (sector, industry)
    """
    yahoo_sector = info.get("sector", "Unknown")
    yahoo_industry = info.get("industry", "Unknown")

    # Priority 1: User-level overrides (from portfolio.json)
    if overrides.get("sector"):
        return overrides["sector"], overrides.get("industry", yahoo_industry)

    # Priority 2: System-level hardcoded overrides
    if symbol.upper() in SECTOR_OVERRIDES:
        sys_override = SECTOR_OVERRIDES[symbol.upper()]
        return sys_override.get("sector", yahoo_sector), sys_override.get("industry", yahoo_industry)

    # Priority 3: Yahoo Finance data
    return yahoo_sector, yahoo_industry


def process_single_position(item: Any) -> Dict[str, Any]:
    """
    Fetches and calculates data for a single portfolio position.

    Args:
        item: Normalized or raw portfolio item.

    Returns:
        Processed stock data dictionary with calculated values.
    """
    meta = get_position_metadata(item)
    symbol = meta["symbol"]
    shares = meta["shares"]

    if not symbol:
        return {}

    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        sector, industry = resolve_classification(symbol, info, meta)
        name = info.get("shortName", symbol)

        # Pricing calculations
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        prev_close = info.get("regularMarketPreviousClose", 0)

        change_pct = 0.0
        if prev_close and prev_close > 0:
            change_pct = ((current_price - prev_close) / prev_close) * 100

        position_value = shares * current_price

        return {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "industry": industry,
            "price": current_price,
            "shares": shares,
            "position_value": round(position_value, 2),
            "change_pct": round(change_pct, 2)
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "name": symbol,
            "sector": "Error",
            "industry": "Error",
            "price": 0,
            "shares": shares,
            "position_value": 0,
            "change_pct": 0,
            "error": str(e)
        }


def fetch_portfolio_data(items: List[Any]) -> Dict[str, Any]:
    """
    Orchestrates fetching and grouping portfolio data for heatmaps.

    Args:
        items: List of portfolio items to process.

    Returns:
        Nested dictionary grouped by sector and industry.
    """
    result = {
        "sectors": {},
        "stocks": [],
        "total_value": 0.0
    }

    for item in items:
        stock_data = process_single_position(item)
        if not stock_data:
            continue

        result["stocks"].append(stock_data)

        if stock_data["sector"] == "Error":
            continue

        position_value = stock_data["position_value"]
        result["total_value"] += position_value

        # Group by Sector
        sector = stock_data["sector"]
        if sector not in result["sectors"]:
            result["sectors"][sector] = {
                "name": sector,
                "industries": {},
                "sector_value": 0.0,
                "stocks": []
            }

        sec_node = result["sectors"][sector]
        sec_node["stocks"].append(stock_data)
        sec_node["sector_value"] += position_value

        # Group by Industry
        industry = stock_data["industry"]
        if industry not in sec_node["industries"]:
            sec_node["industries"][industry] = {
                "name": industry,
                "industry_value": 0.0,
                "stocks": []
            }

        ind_node = sec_node["industries"][industry]
        ind_node["stocks"].append(stock_data)
        ind_node["industry_value"] += position_value

    result["total_value"] = round(result["total_value"], 2)
    return result


def main():
    """Main execution entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No items provided"}))
        sys.exit(1)

    try:
        items = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        sys.exit(1)

    data = fetch_portfolio_data(items)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
