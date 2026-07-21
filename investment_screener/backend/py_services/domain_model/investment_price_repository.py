"""All ``investment_price`` table reads and writes live here (ADR-029 anti-duplication rule)."""

import sqlite3


def upsert_investment_price(
    conn: sqlite3.Connection,
    investment_id: str,
    price: float,
    currency: str,
    fetched_at: str,
) -> None:
    conn.execute(
        "INSERT INTO investment_price (investment_id, price, currency, fetched_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(investment_id) DO UPDATE SET "
        "price=excluded.price, currency=excluded.currency, fetched_at=excluded.fetched_at;",
        (investment_id, price, currency, fetched_at),
    )
    conn.commit()


def get_investment_price(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM investment_price WHERE investment_id = ?;", (investment_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None
