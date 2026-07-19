"""One-time-per-wave backfill: minimal INVESTMENT identity rows for the real ticker universe.

Full field population (lifecycle_status, target_weight, standing_decision, etc.) is Wave 2's
job when target-portfolio.json itself migrates. This script only guarantees every known ticker
has a resolvable investment_id before Wave 1 (projection_version) needs one.
"""

import sqlite3

from domain_model.investment_repository import get_investment, resolve_investment


def backfill_from_ticker_lists(
    conn: sqlite3.Connection,
    tickers: list[str],
    asset_class: str = "EQUITY",
    currency: str = "USD",
) -> int:
    created = 0
    for ticker in tickers:
        existing = get_investment(conn, ticker.upper())
        resolve_investment(conn, ticker, asset_class=asset_class, currency=currency)
        if existing is None:
            created += 1
    return created
