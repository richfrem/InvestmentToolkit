#!/usr/bin/env python3
"""
overnight_gaps.py - Python utility script.

Purpose:
    Overnight / extended-hours gap scanner for portfolio holdings.

Uses yfinance fast_info.last_price (which reflects extended-hours price when
the regular market is closed) vs previous_close to detect significant overnight
moves before the daily brief runs.

Usage:
    python3 overnight_gaps.py                  # scan all portfolio holdings
    python3 overnight_gaps.py NVDA,AAPL,TSLA   # explicit ticker list
    python3 overnight_gaps.py --threshold 3.0  # custom threshold (default: 2.0%)

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Measures pre-market gaps;
      Wave 3 Task 6 cutover — previously portfolio.json)

Layer:
    Backend / Python Services

Usage Examples:
    python3 overnight_gaps.py                  # scan all portfolio holdings
    python3 overnight_gaps.py NVDA,AAPL,TSLA   # explicit ticker list
    python3 overnight_gaps.py --threshold 3.0  # custom threshold (default: 2.0%)

Key Functions (Index):
    - _is_scannable()
    - _load_tickers()
    - _fetch_gap()
    - get_overnight_gaps()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from pathlib import Path
from typing import Any, Optional

import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import list_investments  # noqa: E402
from domain_model.portfolio_repository import load_portfolio_state_from_db  # noqa: E402

REPO_ROOT      = Path(__file__).resolve().parents[3]
DB_PATH        = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

SKIP_SUFFIXES = (".TO", ".V")          # Canadian markets — no extended-hours data via yfinance
SKIP_PATTERNS = ("!", )                # Futures contracts (NQ1!, GC1!) — not supported by yfinance


# Check if a ticker is scannable via extended-hours yfinance
def _is_scannable(ticker: str) -> bool:
    """Return True if ticker is a US equity that yfinance can fetch extended-hours data for.

    Args:
        ticker: Ticker symbol string.

    Returns:
        False for Canadian suffixes (.TO, .V) and futures contracts (NQ1!, GC1!).
    """
    upper = ticker.upper()
    if any(upper.endswith(s) for s in SKIP_SUFFIXES):
        return False
    if any(p in upper for p in SKIP_PATTERNS):
        return False
    return True


# Load active tickers from portfolio and watchlist configs
def _load_tickers(db_path: Path = DB_PATH) -> list[str]:
    """Load scannable tickers from held positions union the watchlisted investments.

    Mirrors the user's curated TradingView BOATS-mylist: active holdings
    plus researched watchlist names, minus Canadian and futures symbols.

    Both holdings (``account_investment``) and watchlist membership
    (``investment.is_watchlisted``) are read from domain_model.sqlite (Wave 3
    Task 6 cutover — previously portfolio.json for holdings).

    Returns:
        Deduplicated list of US equity ticker symbols, order: holdings first.
    """
    seen: set[str] = set()
    tickers: list[str] = []

    if db_path.exists():
        conn = initialize_db(str(db_path))
        try:
            state = load_portfolio_state_from_db(conn)
            for sym in state["shares"]:
                if sym and _is_scannable(sym) and sym not in seen:
                    seen.add(sym)
                    tickers.append(sym)

            for inv in list_investments(conn, is_watchlisted=True):
                sym = inv.get("symbol", "")
                if sym and _is_scannable(sym) and sym not in seen:
                    seen.add(sym)
                    tickers.append(sym)
        finally:
            conn.close()

    return tickers


# Fetch extended-hours gap data for one ticker
def _fetch_gap(ticker: str) -> Optional[dict[str, Any]]:
    """Fetch extended-hours gap data for one ticker.

    Args:
        ticker: US equity ticker symbol.

    Returns:
        Gap dict with ticker, prev_close, current, change_pct, direction,
        and market_state — or None if price data is unavailable.
    """
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        current    = getattr(fi, "last_price", None)
        prev_close = getattr(fi, "previous_close", None)
        if not current or not prev_close or prev_close <= 0:
            return None
        change_pct = (current - prev_close) / prev_close * 100
        try:
            market_state = (t.info or {}).get("marketState", "UNKNOWN")
        except Exception:
            market_state = "UNKNOWN"
        return {
            "ticker":       ticker,
            "prev_close":   round(prev_close, 2),
            "current":      round(current, 2),
            "change_pct":   round(change_pct, 2),
            "direction":    "UP" if change_pct > 0 else "DOWN",
            "market_state": market_state,
        }
    except Exception as e:
        print(f"[overnight_gaps] {ticker}: {e}", file=sys.stderr)
        return None


# Filter and retrieve portfolio holdings with substantial overnight gaps
def get_overnight_gaps(
    tickers: list[str] | None = None,
    threshold_pct: float = 2.0,
) -> list[dict[str, Any]]:
    """Return portfolio holdings with extended-hours moves >= threshold_pct.

    Args:
        tickers: Explicit ticker list. If None, loads from held positions + watchlist (domain_model.sqlite).
        threshold_pct: Minimum absolute % move to include in results.

    Returns:
        Gap dicts sorted by abs(change_pct) descending, filtered to >= threshold_pct.
    """
    if tickers is None:
        tickers = _load_tickers()
    us_tickers = [t for t in tickers if _is_scannable(t)]
    if not us_tickers:
        return []
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(len(us_tickers), 8)) as pool:
        futures = {pool.submit(_fetch_gap, t): t for t in us_tickers}
        try:
            for future in as_completed(futures, timeout=30):
                result = future.result()
                if result and abs(result["change_pct"]) >= threshold_pct:
                    results.append(result)
        except FuturesTimeoutError:
            print("[overnight_gaps] Timeout fetching gap data — returning partial results", file=sys.stderr)
    return sorted(results, key=lambda x: abs(x["change_pct"]), reverse=True)


# Main entry point for CLI scanner execution
def main() -> None:
    """Parses command line options and prints the gap scanner results in JSON format."""
    args = sys.argv[1:]
    threshold: float = 2.0
    explicit_tickers: list[str] | None = None
    i = 0
    while i < len(args):
        if args[i] == "--threshold" and i + 1 < len(args):
            threshold = float(args[i + 1])
            i += 2
        else:
            explicit_tickers = [t.strip().upper() for t in args[i].split(",") if t.strip()]
            i += 1
    print(json.dumps(get_overnight_gaps(explicit_tickers, threshold), indent=2))


if __name__ == "__main__":
    main()
