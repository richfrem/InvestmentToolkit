#!/usr/bin/env python3
"""
fetch_portfolio_heatmap.py (Python Service)
=====================================

Purpose:
    Retrieves and aggregates portfolio data for treemap and sector-based visualizations.
    Performs parallel pre-fetching of yfinance data and historical prices for rapid rendering.
    Supports real-time price injection via TradingView Desktop (optional).

Layer: Backend / Python Services / Data Aggregation

Usage Examples:
    python3 fetch_portfolio_heatmap.py '[{"symbol": "AAPL", "shares": 100}, {"symbol": "MSFT", "shares": 50}]'

Key Functions:
    - fetch_portfolio_data() - Primary orchestrator that manages parallel pre-fetching and result normalization
    - prefetch_info() / prefetch_history() - Utilizes ThreadPoolExecutor for high-concurrency data retrieval
    - _fetch_one() - Atomically fetches and caches yfinance info for a single symbol
"""

import sys
import json
import os
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import yfinance as yf
from history_store import HistoricalPriceStore
from sector_overrides import SECTOR_OVERRIDES
from ticker_aliases import normalize_ticker


class _NpEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)

# --- TradingView connection status (for badge only) ---
# Prices always come from yfinance — TV CLI `quote` reads the active chart only, not per-symbol.
# We still check TV availability so the badge shows connection status correctly.
_TV_AVAILABLE = False
try:
    _TV_PLUGIN_SCRIPTS = str(
        Path(__file__).resolve().parent.parent.parent.parent
        / "plugins" / "tradingview" / "scripts"
    )
    sys.path.insert(0, _TV_PLUGIN_SCRIPTS)
    from tv_client import is_tv_running  # type: ignore[import-not-found]
    _TV_AVAILABLE = is_tv_running()
except Exception:
    pass

# --- Caching Configuration ---
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_DURATION = 900  # 15 minutes



def _cache_path(ticker: str) -> str:
    safe = "".join(c for c in ticker if c.isalnum() or c in ("-", "."))
    return os.path.join(CACHE_DIR, f"{safe}_info.json")


def get_cached_info(ticker: str):
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        if time.time() - os.path.getmtime(path) > CACHE_DURATION:
            return None
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def save_info_to_cache(ticker: str, data: dict) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(ticker), "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _fetch_one(symbol: str) -> tuple[str, dict]:
    """Fetch yfinance info for one symbol, using cache when fresh."""
    cached = get_cached_info(symbol)
    if cached is not None:
        return symbol, cached
    t = yf.Ticker(symbol)
    info = t.info
    # Augment with fast_info so callers get extended-hours price when market is closed.
    try:
        fi = t.fast_info
        info["_fastLastPrice"] = getattr(fi, "last_price", None)
        info["_fastPrevClose"] = getattr(fi, "previous_close", None)
    except Exception:
        pass
    save_info_to_cache(symbol, info)
    return symbol, info


def prefetch_info(symbols: list[str], max_workers: int = 10) -> dict[str, dict]:
    """Fetch yfinance info for all symbols in parallel. Returns symbol→info map."""
    result: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_one, sym): sym for sym in symbols}
        for future in as_completed(futures):
            try:
                sym, info = future.result()
                result[sym] = info
            except Exception as exc:
                sym = futures[future]
                result[sym] = {"_error": str(exc)}
    return result


def prefetch_history(symbols: list[str], history: HistoricalPriceStore, max_workers: int = 10) -> None:
    """Warm the history cache for all symbols in parallel so calc_changes() is instant."""
    def _warm(sym: str) -> None:
        try:
            history.get_or_update(sym)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(_warm, symbols))


def fetch_portfolio_data(items: list) -> dict:
    """Fetch heatmap data for portfolio items with shares."""

    history = HistoricalPriceStore()

    result: dict = {"sectors": {}, "stocks": [], "total_value": 0}

    # --- Normalize items and collect symbols that need yfinance ---
    normalized = []
    to_fetch = []
    for item in items:
        if isinstance(item, str):
            sym, shares, item_sector, item_industry, book_price, stored_price = item, 1, None, None, None, None
        else:
            sym = item.get("symbol", "")
            shares = item.get("shares", 1)
            item_sector = item.get("sector")
            item_industry = item.get("industry")
            book_price = item.get("book_price")
            # "price" is the TV-synced current price; use it instead of yfinance when present
            stored_price = item.get("price") or None
        if not sym:
            continue
        normalized.append((sym, shares, item_sector, item_industry, book_price, stored_price))
        if sym != "USD_CASH":
            to_fetch.append(normalize_ticker(sym))

    # --- Parallel pre-fetch: all yfinance calls batched before the main loop ---
    # prefetch_info and prefetch_history each use ThreadPoolExecutor(max_workers=10)
    # internally, so cold-start fetches for all 30+ tickers complete in ~5-10s total.
    info_map = prefetch_info(to_fetch) if to_fetch else {}
    if to_fetch:
        prefetch_history(to_fetch, history)

    # Track whether any stock used a TV-synced stored price (vs yfinance)
    used_stored_prices = False

    # --- Build result from pre-fetched data ---
    for sym, shares, item_sector, item_industry, book_price, stored_price in normalized:
        try:
            if sym == "USD_CASH":
                name = "USD Cash"
                sector = "CASH"
                industry = "CASH"
                current_price = 1.0
                change_pct = 0.0
                hist_changes: dict = {}
                book_price = 1.0
            else:
                norm_sym = normalize_ticker(sym)
                info = info_map.get(norm_sym, {})
                if "_error" in info:
                    raise RuntimeError(info["_error"])

                yahoo_sector = info.get("sector", "Unknown")
                yahoo_industry = info.get("industry", "Unknown")
                name = info.get("shortName", sym)

                if item_sector:
                    sector = item_sector
                    industry = item_industry or yahoo_industry
                elif sym.upper() in SECTOR_OVERRIDES:
                    override = SECTOR_OVERRIDES[sym.upper()]
                    sector = override.get("sector", yahoo_sector)
                    industry = override.get("industry", yahoo_industry)
                elif norm_sym.upper() in SECTOR_OVERRIDES:
                    override = SECTOR_OVERRIDES[norm_sym.upper()]
                    sector = override.get("sector", yahoo_sector)
                    industry = override.get("industry", yahoo_industry)
                else:
                    sector = yahoo_sector
                    industry = yahoo_industry

                # fast_info.last_price reflects extended-hours (BOATS/pre-market) price.
                # Falls back to regularMarketPrice when fast_info is unavailable.
                yf_price = (info.get("_fastLastPrice")
                            or info.get("currentPrice")
                            or info.get("regularMarketPrice", 0))
                prev_close = info.get("_fastPrevClose") or info.get("regularMarketPreviousClose", 0)
                # Always use live yfinance price for display and change calculations.
                # stored_price may equal book_price (avg fill cost seeded at TV sync) and must
                # NOT be used as current market price — that would give wildly wrong 1D%.
                current_price = yf_price if yf_price and yf_price > 0 else (stored_price or 0)
                change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
                hist_changes = history.calc_changes(norm_sym, current_price)

            total_market = round(shares * current_price, 2)
            total_book = round(shares * book_price, 2) if book_price else None
            change_overall = (
                round(((current_price - book_price) / book_price) * 100, 2)
                if book_price and book_price > 0 and current_price > 0
                else None
            )

            stock_data = {
                "symbol": sym,
                "name": name,
                "sector": sector,
                "industry": industry,
                "price": current_price,
                "book_price": round(book_price, 4) if book_price else None,
                "shares": shares,
                "position_value": total_market,
                "total_market": total_market,
                "total_book": total_book,
                "change_pct": round(change_pct, 2),
                "change_1d": round(change_pct, 2),
                "change_1w": hist_changes.get("change_1w"),
                "change_1m": hist_changes.get("change_1m"),
                "change_ytd": hist_changes.get("change_ytd"),
                "change_1y": hist_changes.get("change_1y"),
                "change_overall": change_overall,
            }

            result["stocks"].append(stock_data)
            result["total_value"] += total_market

            if sector not in result["sectors"]:
                result["sectors"][sector] = {
                    "name": sector,
                    "industries": {},
                    "sector_value": 0,
                    "stocks": [],
                }
            result["sectors"][sector]["stocks"].append(stock_data)
            result["sectors"][sector]["sector_value"] += total_market

            if industry not in result["sectors"][sector]["industries"]:
                result["sectors"][sector]["industries"][industry] = {
                    "name": industry,
                    "industry_value": 0,
                    "stocks": [],
                }
            result["sectors"][sector]["industries"][industry]["stocks"].append(stock_data)
            result["sectors"][sector]["industries"][industry]["industry_value"] += total_market

        except Exception as e:
            result["stocks"].append({
                "symbol": sym,
                "name": sym,
                "sector": "Error",
                "industry": "Error",
                "price": 0,
                "shares": shares,
                "position_value": 0,
                "change_pct": 0,
                "error": str(e),
            })

    result["total_value"] = round(result["total_value"], 2)
    result["price_source"] = "tradingview" if (_TV_AVAILABLE or used_stored_prices) else "yfinance"
    result["refreshed_at"] = datetime.now(timezone.utc).isoformat()
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
    print(json.dumps(data, indent=2, cls=_NpEncoder))


if __name__ == "__main__":
    main()
