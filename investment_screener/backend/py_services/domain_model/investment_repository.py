"""All ``investment`` table reads and writes live here, mirroring
``py_services/intelligence/instrument_repository.py``'s anti-duplication rule (ADR-028,
extended to the domain-model package by ADR-029).
"""

import sqlite3
from datetime import datetime, timezone


def resolve_investment(
    conn: sqlite3.Connection,
    symbol: str,
    asset_class: str = "EQUITY",
    currency: str = "USD",
    name: str | None = None,
) -> str:
    """Return the ``investment_id`` for a symbol, inserting it if new.

    Idempotent: calling this twice for the same symbol returns the same
    ``investment_id`` and does not insert a duplicate row.
    """
    cursor = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (symbol,))
    row = cursor.fetchone()
    if row:
        return row[0]
    investment_id = symbol.upper()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, name, asset_class, currency, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (investment_id, symbol, name or symbol, asset_class, currency, now),
    )
    conn.commit()
    return investment_id


def get_investment(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    """Return the investment row as a dict, or ``None`` if it doesn't exist."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM investment WHERE investment_id = ?;", (investment_id,))
    row = cursor.fetchone()
    return dict(row) if row else None
