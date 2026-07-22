"""All ``broker_reported_total`` table reads and writes live here (ADR-029 anti-duplication rule).

Singleton table (one row, id=1): the broker's OWN last-reported portfolio total
(``totals.totalUSD``/``totalCAD``/``totalSource`` in the portfolio.json sync payload).
Per ADR-030's Wave 3 addendum pattern, this is a broker-reported FACT the schema
cannot recompute — captured for exactly one consumer: verify_portfolio_total.py's
reconciliation audit, which compares this figure against get_portfolio_total_value()'s
computed total. It is NOT "the" authoritative total (computation remains authoritative);
it is only the audited-against comparison source. Overwritten each sync, mirroring
broker_exchange_rate.
"""

import sqlite3


def upsert_broker_reported_total(
    conn: sqlite3.Connection,
    total_usd: float,
    total_cad: float | None,
    synced_at: str,
    source: str | None = None,
) -> None:
    """Idempotently store the single broker-reported total row (id=1), overwriting each sync."""
    conn.execute(
        "INSERT INTO broker_reported_total (id, total_usd, total_cad, synced_at, source) "
        "VALUES (1, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "total_usd=excluded.total_usd, total_cad=excluded.total_cad, "
        "synced_at=excluded.synced_at, source=excluded.source;",
        (total_usd, total_cad, synced_at, source),
    )
    conn.commit()


def get_broker_reported_total(conn: sqlite3.Connection) -> dict | None:
    """Return the stored broker-reported total as a dict, or None if never synced."""
    row = conn.execute(
        "SELECT total_usd, total_cad, synced_at, source "
        "FROM broker_reported_total WHERE id = 1;"
    ).fetchone()
    if row is None:
        return None
    return {
        "total_usd": row[0],
        "total_cad": row[1],
        "synced_at": row[2],
        "source": row[3],
    }
