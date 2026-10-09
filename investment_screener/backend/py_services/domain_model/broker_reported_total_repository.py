"""broker_reported_total_repository.py - Reads and writes of the broker_reported_total table.

Purpose:
    All ``broker_reported_total`` table reads and writes live here (ADR-029 anti-duplication rule).

    Singleton table (one row, id=1): the broker's OWN last-reported portfolio total
    (totalUSD, totalCAD and the source label, as carried by ``totals.totalUSD``/``totalCAD``/
    ``totalSource`` in the retired portfolio.json sync payload; each broker sync now writes them
    straight to this table).
        Per ADR-030's Wave 3 addendum pattern, this is a broker-reported FACT the schema
    cannot recompute - captured for exactly one consumer: verify_portfolio_total.py's
    reconciliation audit, which compares this figure against get_portfolio_total_value()'s
    computed total. It is NOT "the" authoritative total (computation remains authoritative);
    it is only the audited-against comparison source. Overwritten each sync, mirroring
    broker_exchange_rate.

Layer:
    Backend / Python Services / Domain Model

Usage Examples:
    upsert_broker_reported_total(conn, 33735.62, 46538.29, "2026-10-09T15:24:41+00:00", "tv_authoritative")
    row = get_broker_reported_total(conn)  # {"total_usd": ..., "total_cad": ..., "synced_at": ..., "source": ...}

Key Functions (Index):
    - upsert_broker_reported_total(): overwrite the single row (id=1) after a broker sync
    - get_broker_reported_total(): read the row, or None if never synced

Key Input Dependencies:
    - An open domain_model.sqlite connection with the broker_reported_total table (schema_migrator)

Key Output Dependencies:
    - Written by plugins/tradingview/scripts/fetch_broker_data.py and plugins/questrade/scripts/questrade_sync.py
    - Read by py_services/verify_portfolio_total.py
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
