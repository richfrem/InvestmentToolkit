#!/usr/bin/env python3
"""
batch_update_price_levels.py — Batch calculate and synchronize price levels for TradingView.
=============================================================================================

Purpose:
    Provides a unified utility to batch calculate, persist, and synchronize structured price
    levels across all watchlist and portfolio investments in TradingView.
    
    Addresses the TradingView chart architecture where the AI TA Levels indicator runs on
    a single chart canvas:
      1. Batch recalculates fresh combined levels (DCF tiers + technical chart levels) in SQLite.
      2. Offers --follow mode to automatically sync levels in real-time as the user clicks
         tickers in their TradingView watchlist without triggering warning banners.
      3. Offers --sweep mode to sequentially iterate through the watchlist in TradingView Desktop
         and verify that every chart draws its levels cleanly.

Layer:
    Plugins / TradingView / Operating TradingView Charts / Scripts

Usage Examples:
    # Recalculate & persist fresh levels for all followed watchlist/portfolio names:
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --recalculate

    # Launch real-time follower so clicking any stock in TradingView updates levels dynamically:
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --follow

    # Sequentially sweep through all watchlist charts in TradingView Desktop:
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep

    # Single-ticker update and draw:
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --ticker NFLX

Key Functions:
    - batch_recalculate_levels() — Persists fresh price levels in domain_model.sqlite
    - batch_draw_watchlist()     — Sequentially switches and draws charts in TradingView Desktop
    - get_followed_tickers()     — Reads active portfolio holdings and watchlisted symbols
    - start_follower()           — Runs background follower daemon for live watchlist clicking

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Projections & Watchlists)
    - investment_screener/backend/py_services/update_price_levels.py (Tiers calculation engine)
    - investment_screener/backend/py_services/pine_level_inputs.py (CDP indicator input manipulation)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Resolve project root and backend services directory
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())
ENGINE_DIR = PROJECT_ROOT / "investment_screener/backend/py_services"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from pine_level_inputs import draw_levels, follow
from update_price_levels import derive_and_write, derive_and_write_followed


def get_followed_tickers(db_path: str | Path | None = None) -> List[str]:
    """Retrieve all symbols in scope (active holdings and watchlisted stocks) from domain_model.sqlite.

    Args:
        db_path: Optional custom path to domain_model.sqlite.

    Returns:
        Sorted list of uppercase ticker symbols.
    """
    import review_cycle
    from domain_model.db_client import initialize_db

    db_file = str(db_path or (PROJECT_ROOT / "investment_screener/backend/data/domain_model.sqlite"))
    conn = initialize_db(db_file)
    try:
        items = review_cycle.in_scope(conn)
        return sorted({item["symbol"].upper() for item in items if item.get("symbol") and item["symbol"] != "CASH_USD"})
    finally:
        conn.close()


def batch_recalculate_levels(
    source: str = "combined",
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Recalculate and persist price levels in SQLite for all followed portfolio & watchlist names.

    Args:
        source: Tier derivation strategy ('combined', 'dcf', 'ta', etc.).
        dry_run: When True, computes tiers without committing to database.
        db_path: Optional path to domain_model.sqlite.

    Returns:
        Dictionary summary containing 'updated', 'skipped', and 'failed' lists.
    """
    dbp = Path(db_path) if db_path else None
    return derive_and_write_followed(source=source, dry_run=dry_run, db_path=dbp)


def batch_draw_watchlist(
    tickers: Optional[List[str]] = None,
    delay: float = 1.5,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Sequentially switch TradingView Desktop charts and draw stored levels.

    Args:
        tickers: Optional list of tickers. If None, reads followed tickers from database.
        delay: Seconds to pause between charts to allow DOM and chart renderer to settle.
        db_path: Optional path to domain_model.sqlite.

    Returns:
        Dictionary summary with total, drawn, and failed tickers.
    """
    symbols = tickers if tickers is not None else get_followed_tickers(db_path)
    drawn: List[str] = []
    failed: List[Dict[str, str]] = []

    print(f"Beginning sequential chart sweep for {len(symbols)} tickers (delay: {delay}s)...")
    for symbol in symbols:
        try:
            res = draw_levels(symbol, db_path=db_path, switch=True)
            if isinstance(res, dict) and res.get("success"):
                drawn.append(symbol)
                print(f"  ✓ {symbol}: levels set on '{res.get('study')}'")
            else:
                err_msg = res.get("error", str(res)) if isinstance(res, dict) else str(res)
                failed.append({"ticker": symbol, "error": err_msg})
                print(f"  ✗ {symbol}: {err_msg}", file=sys.stderr)
        except Exception as exc:
            failed.append({"ticker": symbol, "error": str(exc)})
            print(f"  ✗ {symbol}: {type(exc).__name__}: {exc}", file=sys.stderr)
        
        if delay > 0:
            time.sleep(delay)

    return {"total": len(symbols), "drawn": drawn, "failed": failed}


def start_follower(interval: float = 1.5, db_path: str | Path | None = None) -> None:
    """Launch the background symbol follower daemon.

    Polls the active chart symbol in TradingView Desktop via CDP port 9222 and
    automatically sets and draws the stored levels whenever the user clicks or
    changes tickers.

    Args:
        interval: Polling frequency in seconds.
        db_path: Optional path to domain_model.sqlite.
    """
    print("Starting TradingView live symbol follower daemon...")
    print("Clicking any ticker in your TradingView watchlist will auto-update levels.")
    print("Press Ctrl+C to terminate.")
    follow(interval=interval, db_path=db_path)


def main() -> int:
    """CLI entry point for batch updating TradingView price levels."""
    parser = argparse.ArgumentParser(
        description="Batch calculate, persist, and synchronize TradingView price levels."
    )
    parser.add_argument(
        "--recalculate",
        action="store_true",
        help="Batch recalculate and persist levels in SQLite for all followed names",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Sequentially switch TradingView charts and draw levels for all watchlist names",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Run real-time background follower to auto-draw levels on watchlist clicks",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="Recalculate and draw levels for a specific ticker",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="combined",
        choices=["combined", "dcf", "ta", "manual"],
        help="Price level derivation source (default: combined)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay in seconds between charts during sequential sweep (default: 1.5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate levels without committing to database or updating chart",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to domain_model.sqlite",
    )

    args = parser.parse_args()

    # Case 1: Specific ticker
    if args.ticker:
        sym = args.ticker.upper()
        print(f"Recalculating price levels for {sym} (source={args.source}, dry_run={args.dry_run})...")
        dbp = Path(args.db) if args.db else None
        res = derive_and_write(sym, source=args.source, dry_run=args.dry_run, db_path=dbp)
        print(json.dumps(res, indent=2))
        if not args.dry_run:
            print(f"Drawing levels for {sym} on active TradingView chart...")
            drawn = draw_levels(sym, db_path=dbp, switch=True)
            if isinstance(drawn, dict) and drawn.get("success"):
                print(f"✓ Levels successfully drawn for {sym} on '{drawn.get('study')}'.")
            else:
                print(f"✗ Could not draw levels for {sym}: {drawn}", file=sys.stderr)
                return 1
        return 0

    # Case 2: Live follower daemon
    if args.follow:
        try:
            start_follower(interval=args.delay, db_path=args.db)
            return 0
        except KeyboardInterrupt:
            print("\nFollower stopped.")
            return 0

    # Case 3: Sequential sweep across charts
    if args.sweep:
        res = batch_draw_watchlist(delay=args.delay, db_path=args.db)
        print(f"\nSweep completed: {len(res['drawn'])}/{res['total']} charts drawn successfully.")
        if res["failed"]:
            print(f"Failed charts ({len(res['failed'])}):", file=sys.stderr)
            for item in res["failed"]:
                print(f"  {item['ticker']}: {item['error']}", file=sys.stderr)
            return 1
        return 0

    # Case 4: Default or explicit recalculate
    print(f"Batch recalculating price levels for all followed tickers (source={args.source}, dry_run={args.dry_run})...")
    res = batch_recalculate_levels(source=args.source, dry_run=args.dry_run, db_path=args.db)
    print(
        f"Completed: {len(res['updated'])} updated, {len(res['skipped'])} skipped, {len(res['failed'])} failed."
    )
    if res["failed"]:
        for item in res["failed"]:
            print(f"  ✗ {item['ticker']}: {item['reason']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
