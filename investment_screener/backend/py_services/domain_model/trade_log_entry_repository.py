"""All ``trade_log_entry`` table reads and writes live here. This table is the
local trade log -- the manually/agent-logged record of planned and executed
trades (spec s2.7, Domain Data Model v3.2). Keyed by ``entry_id``.

Callers resolve ``investment_id`` via ``investment_repository.resolve_investment()``
before calling ``upsert_trade_log_entry`` -- this module is a pure repository over
the DDL's own column names and does not translate JSON source keys
(e.g. ``ticker`` -> ``investment_id``, ``totalCost`` -> ``total_cost``); that
translation is the migration script's job.

Note: the JSON source (``data/trade-log.json``) also carries ``extendedHours``
and ``tvOrderId`` fields that have no corresponding column in the
``trade_log_entry`` DDL. They are intentionally not persisted here.
"""

import sqlite3

_COLUMNS = (
    "entry_id", "investment_id", "account_id", "action", "shares", "price",
    "total_cost", "order_type", "limit_price", "trade_date", "notes",
    "status", "source", "priority", "logged_at",
)


def upsert_trade_log_entry(conn: sqlite3.Connection, entry: dict) -> str:
    values = tuple(entry.get(col) for col in _COLUMNS)
    placeholders = ", ".join(["?"] * len(_COLUMNS))
    update_clause = ", ".join(
        f"{col}=excluded.{col}" for col in _COLUMNS if col != "entry_id"
    )
    conn.execute(
        f"INSERT INTO trade_log_entry ({', '.join(_COLUMNS)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(entry_id) DO UPDATE SET {update_clause};",
        values,
    )
    conn.commit()
    return entry["entry_id"]


def list_trade_log_entries(
    conn: sqlite3.Connection,
    account_id: str | None = None,
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM trade_log_entry WHERE 1=1"
    params: list = []
    if account_id:
        query += " AND account_id = ?"
        params.append(account_id)
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def get_trade_log_entry(conn: sqlite3.Connection, entry_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM trade_log_entry WHERE entry_id = ?", (entry_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_trade_log_entry(conn: sqlite3.Connection, entry_id: str) -> None:
    conn.execute("DELETE FROM trade_log_entry WHERE entry_id = ?", (entry_id,))
    conn.commit()
