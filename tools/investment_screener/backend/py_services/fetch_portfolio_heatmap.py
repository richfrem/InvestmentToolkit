#!/usr/bin/env python3
"""
fetch_portfolio_heatmap.py - Fetches portfolio data for treemap visualization.

Now accepts items with shares to calculate actual portfolio values.
Optimized with local filesystem caching (15 minutes) for Yahoo Finance data.

Usage:
    python3 fetch_portfolio_heatmap.py '[{"symbol": "AAPL", "shares": 100}, ...]'
"""

import sys
import json
import os
import time
import yfinance as yf

# --- Caching Configuration ---
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_DURATION = 900  # 15 minutes in seconds

def get_cached_info(ticker):
    """Retrieve cached stock info if valid."""
    if not os.path.exists(CACHE_DIR):
        return None
    
    # Simple sanitization for filename
    safe_ticker = "".join([c for c in ticker if c.isalnum() or c in ('-','.')])
    cache_file = os.path.join(CACHE_DIR, f"{safe_ticker}_info.json") # Different suffix to avoid collision if schema differs
    
    if not os.path.exists(cache_file):
        return None
        
    try:
        # Check expiration
        if time.time() - os.path.getmtime(cache_file) > CACHE_DURATION:
            return None
            
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def save_info_to_cache(ticker, data):
    """Save stock info to cache."""
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        safe_ticker = "".join([c for c in ticker if c.isalnum() or c in ('-','.')])
        cache_file = os.path.join(CACHE_DIR, f"{safe_ticker}_info.json")
        
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def fetch_portfolio_data(items: list) -> dict:
    """Fetch heatmap data for portfolio items with shares."""
    
    # Sector/industry overrides for stocks Yahoo doesn't classify correctly
    SECTOR_OVERRIDES = {
        "HUMN": {"sector": "Technology", "industry": "Software - Application"},
        "KOID": {"sector": "Technology", "industry": "Software - Application"},
        "IBIT": {"sector": "Cryptocurrency", "industry": "Bitcoin ETF"},
        "SOLZ": {"sector": "Cryptocurrency", "industry": "Crypto Assets"},
        "ETHA": {"sector": "Cryptocurrency", "industry": "Ethereum ETF"},
        "COIN": {"sector": "Cryptocurrency", "industry": "Crypto Exchange"},
    }
    
    result = {
        "sectors": {},
        "stocks": [],
        "total_value": 0
    }
    
    for item in items:
        # Handle both old format (string) and new format (object)
        if isinstance(item, str):
            symbol = item
            shares = 1  # Default to 1 share for old format
            item_sector = None
            item_industry = None
        else:
            symbol = item.get("symbol", "")
            shares = item.get("shares", 1)
            item_sector = item.get("sector")  # User override from JSON
            item_industry = item.get("industry")  # User override from JSON
        
        if not symbol:
            continue
            
        try:
            # TRY CACHE FIRST
            info = get_cached_info(symbol)
            
            if not info:
                # Fetch if not in cache
                stock = yf.Ticker(symbol)
                info = stock.info
                # Save to cache
                save_info_to_cache(symbol, info)
            
            # Get basic info with override support
            # Priority: 1) portfolio.json override, 2) SECTOR_OVERRIDES, 3) Yahoo data
            yahoo_sector = info.get("sector", "Unknown")
            yahoo_industry = info.get("industry", "Unknown")
            name = info.get("shortName", symbol)
            
            # Use portfolio.json override if present
            if item_sector:
                sector = item_sector
                industry = item_industry or yahoo_industry
            # Apply hardcoded overrides for known issues
            elif symbol.upper() in SECTOR_OVERRIDES:
                override = SECTOR_OVERRIDES[symbol.upper()]
                sector = override.get("sector", yahoo_sector)
                industry = override.get("industry", yahoo_industry)
            else:
                sector = yahoo_sector
                industry = yahoo_industry
            
            # Get price change
            current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            prev_close = info.get("regularMarketPreviousClose", 0)
            
            if prev_close and prev_close > 0:
                change_pct = ((current_price - prev_close) / prev_close) * 100
            else:
                change_pct = 0
            
            # Calculate portfolio value for this position
            position_value = shares * current_price
            
            stock_data = {
                "symbol": symbol,
                "name": name,
                "sector": sector,
                "industry": industry,
                "price": current_price,
                "shares": shares,
                "position_value": round(position_value, 2),
                "change_pct": round(change_pct, 2)
            }
            
            result["stocks"].append(stock_data)
            result["total_value"] += position_value
            
            # Group by sector
            if sector not in result["sectors"]:
                result["sectors"][sector] = {
                    "name": sector,
                    "industries": {},
                    "sector_value": 0,
                    "stocks": []
                }
            
            result["sectors"][sector]["stocks"].append(stock_data)
            result["sectors"][sector]["sector_value"] += position_value
            
            # Group by industry within sector
            if industry not in result["sectors"][sector]["industries"]:
                result["sectors"][sector]["industries"][industry] = {
                    "name": industry,
                    "industry_value": 0,
                    "stocks": []
                }
            result["sectors"][sector]["industries"][industry]["stocks"].append(stock_data)
            result["sectors"][sector]["industries"][industry]["industry_value"] += position_value
            
        except Exception as e:
            # Add error entry for failed symbols
            result["stocks"].append({
                "symbol": symbol,
                "name": symbol,
                "sector": "Error",
                "industry": "Error",
                "price": 0,
                "shares": shares,
                "position_value": 0,
                "change_pct": 0,
                "error": str(e)
            })
    
    result["total_value"] = round(result["total_value"], 2)
    return result


def main():
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