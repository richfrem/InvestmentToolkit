"""All ``broker_exchange_rate`` table reads and writes live here (ADR-029 anti-duplication rule).

Singleton table (one row, id=1): the single broker-reported USD->CAD FX fact,
inferred at sync time from TradingView's own native totals per CLAUDE.md pitfall
#27. Per ADR-030's Wave 3 addendum, only this scalar rate is stored — never a
CAD-denominated total. Callers fall back to a static default when it returns None
(fresh/never-synced DB), matching this codebase's existing fallback conventions.
"""

import sqlite3


def upsert_exchange_rate(
    conn: sqlite3.Connection,
    usd_to_cad_rate: float,
    synced_at: str,
) -> None:
    """Idempotently store the single USD->CAD rate row (id=1), overwriting each sync."""
    conn.execute(
        "INSERT INTO broker_exchange_rate (id, usd_to_cad_rate, synced_at) "
        "VALUES (1, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "usd_to_cad_rate=excluded.usd_to_cad_rate, synced_at=excluded.synced_at;",
        (usd_to_cad_rate, synced_at),
    )
    conn.commit()


def get_exchange_rate(conn: sqlite3.Connection) -> float | None:
    """Return the stored USD->CAD rate, or None if never synced."""
    row = conn.execute(
        "SELECT usd_to_cad_rate FROM broker_exchange_rate WHERE id = 1;"
    ).fetchone()
    return row[0] if row else None
