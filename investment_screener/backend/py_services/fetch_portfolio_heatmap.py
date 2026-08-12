#!/usr/bin/env python3
"""
fetch_portfolio_heatmap.py - Python utility script.

Purpose:
    Retrieves and aggregates portfolio data for treemap and sector-based visualizations.
    Performs parallel pre-fetching of yfinance data and historical prices for rapid rendering.
    Supports real-time price injection via TradingView Desktop (optional).

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - _NpEncoder()
    - default()
    - _cache_path()
    - get_cached_info()
    - save_info_to_cache()
    - _fetch_one()
    - prefetch_info()
    - prefetch_history()
    - _warm()
    - fetch_portfolio_data()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
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


def _fetch_one(symbol: str, bust_cache: bool = False) -> tuple[str, dict]:
    """Fetch yfinance info for one symbol, using cache when fresh.

    Args:
        symbol: The ticker symbol to fetch.
        bust_cache: When True, bypass the cache and force a live yfinance fetch.
    """
    if not bust_cache:
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


def prefetch_info(symbols: list[str], max_workers: int = 10, bust_cache: bool = False) -> dict[str, dict]:
    """Fetch yfinance info for all symbols in parallel. Returns symbol→info map.

    Args:
        symbols: List of ticker symbols to fetch.
        max_workers: Thread pool size.
        bust_cache: When True, bypass the 15-minute cache and force live yfinance fetches.
    """
    result: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_one, sym, bust_cache): sym for sym in symbols}
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


def fetch_portfolio_data(items: list, bust_cache: bool = False) -> dict:
    """Fetch heatmap data for portfolio items with shares.

    Args:
        items: List of portfolio holding dicts (symbol, shares, book_price, …).
        bust_cache: When True, bypass the 15-minute yfinance cache. Use for
            explicit user-triggered refreshes so prices are always live.
    """
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
    info_map = prefetch_info(to_fetch, bust_cache=bust_cache) if to_fetch else {}

    # --- TradingView price overlay (primary source) ---
    # Reads live prices from the "TV-Full Watchlist" TradingView watchlist via CDP.
    # tv_batch_quotes.batch_quotes() already applies session-aware price selection
    # (regular -> extended hours -> overnight/BOATS), so q["price"] here is always
    # the current tradable price, not a frozen post-close regular price.
    # Overrides yfinance price in info_map.
    try:
        import sys as _sys
        _tv_scripts = str(Path(__file__).resolve().parents[3] / "plugins/tradingview/scripts")
        if _tv_scripts not in _sys.path:
            _sys.path.insert(0, _tv_scripts)
        from tv_batch_quotes import batch_quotes as _tv_batch  # type: ignore[import]
        tv_result = _tv_batch(to_fetch)
        for sym, q in tv_result.get("quotes", {}).items():
            if q.get("source") == "tradingview" and sym in info_map:
                info_map[sym]["_fastLastPrice"] = q["price"]
                info_map[sym]["_fastChangePct"] = q.get("changePercent")
    except Exception:
        pass
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

                # Price priority: TradingView live → yfinance fast_info → post/pre-market → current/regular
                yf_price = (info.get("_fastLastPrice")
                            or info.get("postMarketPrice")
                            or info.get("preMarketPrice")
                            or info.get("currentPrice")
                            or info.get("regularMarketPrice", 0))
                prev_close = info.get("_fastPrevClose") or info.get("regularMarketPreviousClose", 0)
                # Always use live price for display and change calculations.
                # stored_price may equal book_price (avg fill cost seeded at TV sync) and must
                # NOT be used as current market price — that would give wildly wrong 1D%.
                current_price = yf_price if yf_price and yf_price > 0 else (stored_price or 0)
                # Use TV-provided change% when available (reflects live TradingView session)
                tv_change_pct = info.get("_fastChangePct")
                change_pct = tv_change_pct if tv_change_pct is not None else (
                    ((current_price - prev_close) / prev_close * 100) if prev_close else 0
                )
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

    bust_cache = "--bust-cache" in sys.argv[2:]
    data = fetch_portfolio_data(items, bust_cache=bust_cache)
    print(json.dumps(data, indent=2, cls=_NpEncoder))


if __name__ == "__main__":
    main()
