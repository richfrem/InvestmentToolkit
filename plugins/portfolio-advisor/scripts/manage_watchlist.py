#!/usr/bin/env python3
"""
manage_watchlist.py - Watchlist operations & domain_model.sqlite persistence utility.
=====================================================================================

Purpose:
    Canonical CLI and service module for managing watchlisted equities in domain_model.sqlite.
    Provides safe, atomic methods to insert/update ticker entries, assign strategy pillars,
    record live prices in investment_price, update lifecycle statuses, and retrieve active lists.

Layer:
    Portfolio Advisor / Scripts & Python Services

Usage Examples:
    python3 manage_watchlist.py --add MP --name "MP Materials Corp." --pillar defense --sub-strategy defense-ai-space --price 54.11
    python3 manage_watchlist.py --remove MP
    python3 manage_watchlist.py --list
    python3 manage_watchlist.py --list --json

Key Functions (Index):
    - get_db_connection(db_path) -> sqlite3.Connection
    - add_to_watchlist(ticker, db_path, name, pillar_id, sub_strategy_id, price, sector, industry, latest_projection_id) -> dict
    - remove_from_watchlist(ticker, db_path) -> dict
    - get_watchlist_items(db_path) -> list[dict]
    - main() -> CLI parser and dispatcher

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite

Key Output Dependencies:
    - Writes to investment and investment_price tables in domain_model.sqlite
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Default path to the SQLite single source of truth
_HERE: Path = Path(__file__).resolve().parent
_DEFAULT_DB: Path = _HERE.parents[2] / "investment_screener" / "backend" / "data" / "domain_model.sqlite"
if not _DEFAULT_DB.exists():
    _DEFAULT_DB = _HERE.parents[1] / "investment_screener" / "backend" / "data" / "domain_model.sqlite"
if not _DEFAULT_DB.exists():
    _DEFAULT_DB = _HERE / ".." / "data" / "domain_model.sqlite"


# Dual-layer docs: get_db_connection helper
def get_db_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Establish and return an active sqlite3 connection configured with Row factory.

    Args:
        db_path: Optional explicit file path to SQLite database.

    Returns:
        sqlite3.Connection: Active database connection with sqlite3.Row row_factory.
    """
    path = Path(db_path) if db_path else _DEFAULT_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


# Dual-layer docs: add_to_watchlist function
def add_to_watchlist(
    ticker: str,
    db_path: str | Path | None = None,
    name: str | None = None,
    pillar_id: str | None = None,
    sub_strategy_id: str | None = None,
    price: float | None = None,
    sector: str | None = None,
    industry: str | None = None,
    latest_projection_id: str | None = None,
) -> dict[str, Any]:
    """Insert or update an equity as an active watchlisted item in domain_model.sqlite.

    Args:
        ticker: Stock ticker symbol (e.g. 'MP', 'NVDA').
        db_path: Optional explicit database path.
        name: Full company name.
        pillar_id: Strategy pillar identifier (e.g. 'defense', 'compute').
        sub_strategy_id: Sub-strategy identifier (e.g. 'defense-ai-space').
        price: Latest market price to record in investment_price.
        sector: Economic sector.
        industry: Specific industry classification.
        latest_projection_id: Foreign key ID to projection_version.

    Returns:
        dict[str, Any]: Execution status payload.
    """
    ticker_clean = ticker.upper().strip()
    conn = get_db_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        cur = conn.execute(
            "SELECT investment_id, name, pillar_id, sub_strategy_id FROM investment WHERE symbol = ?",
            (ticker_clean,),
        )
        row = cur.fetchone()

        if row:
            inv_id = row["investment_id"]
            conn.execute(
                """
                UPDATE investment
                SET is_watchlisted = 1,
                    watchlist_added_at = COALESCE(watchlist_added_at, ?),
                    lifecycle_status = CASE WHEN lifecycle_status = 'holding' THEN 'holding' ELSE 'watchlist' END,
                    name = COALESCE(?, name),
                    pillar_id = COALESCE(?, pillar_id),
                    sub_strategy_id = COALESCE(?, sub_strategy_id),
                    sector = COALESCE(?, sector),
                    industry = COALESCE(?, industry),
                    latest_projection_id = COALESCE(?, latest_projection_id),
                    updated_at = ?
                WHERE investment_id = ?
                """,
                (now, name, pillar_id, sub_strategy_id, sector, industry, latest_projection_id, now, inv_id),
            )
        else:
            inv_id = ticker_clean
            conn.execute(
                """
                INSERT INTO investment (
                    investment_id, symbol, name, asset_class, currency,
                    lifecycle_status, target_weight, pillar_id, sub_strategy_id,
                    is_watchlisted, watchlist_added_at, sector, industry, latest_projection_id, updated_at
                ) VALUES (?, ?, ?, 'EQUITY', 'USD', 'watchlist', 0.0, ?, ?, 1, ?, ?, ?, ?, ?)
                """,
                (inv_id, ticker_clean, name or ticker_clean, pillar_id, sub_strategy_id, now, sector, industry, latest_projection_id, now),
            )

        if price is not None:
            conn.execute(
                """
                INSERT INTO investment_price (investment_id, price, currency, fetched_at)
                VALUES (?, ?, 'USD', ?)
                ON CONFLICT(investment_id) DO UPDATE SET
                    price = excluded.price,
                    fetched_at = excluded.fetched_at
                """,
                (inv_id, float(price), now),
            )

        conn.commit()
        return {"success": True, "ticker": ticker_clean, "status": "watchlisted", "pillar": pillar_id}
    finally:
        conn.close()


# Dual-layer docs: remove_from_watchlist function
def remove_from_watchlist(ticker: str, db_path: str | Path | None = None) -> dict[str, Any]:
    """Remove an equity from the active watchlist (sets is_watchlisted = 0).

    Args:
        ticker: Stock ticker symbol.
        db_path: Optional explicit database path.

    Returns:
        dict[str, Any]: Execution status payload.
    """
    ticker_clean = ticker.upper().strip()
    conn = get_db_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            """
            UPDATE investment
            SET is_watchlisted = 0,
                lifecycle_status = CASE WHEN lifecycle_status = 'watchlist' THEN 'exit' ELSE lifecycle_status END,
                updated_at = ?
            WHERE symbol = ?
            """,
            (now, ticker_clean),
        )
        conn.commit()
        return {"success": True, "ticker": ticker_clean, "status": "unwatchlisted"}
    finally:
        conn.close()


# Dual-layer docs: get_watchlist_items function
def get_watchlist_items(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Retrieve all active watchlisted equities from domain_model.sqlite.

    Args:
        db_path: Optional explicit database path.

    Returns:
        list[dict[str, Any]]: List of dictionary representations of watchlisted rows.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT i.symbol, i.name, i.is_watchlisted, i.pillar_id, i.sub_strategy_id,
                   i.lifecycle_status, i.target_weight, ip.price, i.latest_projection_id
            FROM investment i
            LEFT JOIN investment_price ip ON i.investment_id = ip.investment_id
            WHERE i.is_watchlisted = 1
            ORDER BY i.symbol ASC
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# Dual-layer docs: CLI entrypoint
def main() -> None:
    """Parse CLI flags and dispatch watchlist management operations."""
    parser = argparse.ArgumentParser(description="Manage watchlisted equities in domain_model.sqlite")
    parser.add_argument("--add", help="Ticker to add to watchlist")
    parser.add_argument("--remove", help="Ticker to remove from watchlist")
    parser.add_argument("--list", action="store_true", help="List all active watchlisted tickers")
    parser.add_argument("--pillar", help="Pillar ID (e.g. compute, power, defense)")
    parser.add_argument("--sub-strategy", help="Sub-strategy ID")
    parser.add_argument("--price", type=float, help="Current market price")
    parser.add_argument("--name", help="Company Name")
    parser.add_argument("--sector", help="Sector")
    parser.add_argument("--industry", help="Industry")
    parser.add_argument("--projection-id", help="Latest projection ID")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.add:
        res = add_to_watchlist(
            ticker=args.add,
            name=args.name,
            pillar_id=args.pillar,
            sub_strategy_id=args.sub_strategy,
            price=args.price,
            sector=args.sector,
            industry=args.industry,
            latest_projection_id=args.projection_id,
        )
        print(json.dumps(res, indent=2) if args.json else f"✅ Added {args.add} to watchlist.")
    elif args.remove:
        res = remove_from_watchlist(ticker=args.remove)
        print(json.dumps(res, indent=2) if args.json else f"🗑️ Removed {args.remove} from watchlist.")
    elif args.list:
        items = get_watchlist_items()
        if args.json:
            print(json.dumps(items, indent=2))
        else:
            print(f"📋 Active Watchlist ({len(items)} items):")
            for it in items:
                print(
                    f"  • {it['symbol']:<6} | {it.get('name', '')[:25]:<25} | "
                    f"Pillar: {it.get('pillar_id') or 'None':<10} | Price: ${it.get('price') or 0:.2f}"
                )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
