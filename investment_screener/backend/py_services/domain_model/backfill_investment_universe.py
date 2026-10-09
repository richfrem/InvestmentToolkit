"""backfill_investment_universe.py - Create minimal investment identity rows for a ticker list.

Purpose:
    One-time-per-wave backfill: minimal INVESTMENT identity rows for the real ticker universe.
    Full field population (lifecycle_status, target_weight, standing_decision, etc.) was Wave 2's
    job, done by migrate_target_portfolio_to_sqlite.py when the retired target-portfolio.json
    migrated. This module only guarantees every known ticker has a resolvable investment_id
    before Wave 1 (projection_version) needs one.

Layer:
    Backend / Python Services / Domain Model

Usage Examples:
    from domain_model.backfill_investment_universe import backfill_from_ticker_lists
    created = backfill_from_ticker_lists(conn, ["AAPL", "MSFT"])

Key Functions (Index):
    - backfill_from_ticker_lists(): resolve each ticker, inserting a row when new

Key Input Dependencies:
    - An open domain_model.sqlite connection (see db_client.initialize_db)
    - domain_model/investment_repository.py (get_investment, resolve_investment)

Key Output Dependencies:
    - investment table rows (identity columns only)
"""

import sqlite3

from domain_model.investment_repository import get_investment, resolve_investment


def backfill_from_ticker_lists(
    conn: sqlite3.Connection,
    tickers: list[str],
    asset_class: str = "EQUITY",
    currency: str = "USD",
) -> int:
    """Ensure an ``investment`` row exists for every ticker; return how many were new.

    Idempotent: a ticker that already has a row is left untouched.

    Args:
        conn: Open domain-model connection.
        tickers: Ticker symbols to guarantee (case-insensitive for the existence check).
        asset_class: asset_class given to newly created rows.
        currency: currency given to newly created rows.

    Returns:
        Number of rows created by this call.
    """
    created = 0
    for ticker in tickers:
        existing = get_investment(conn, ticker.upper())
        resolve_investment(conn, ticker, asset_class=asset_class, currency=currency)
        if existing is None:
            created += 1
    return created
