"""All ``trade_log_entry`` table reads and writes live here. This table is the
local trade log -- the manually/agent-logged record of planned and executed
trades (spec s2.7, Domain Data Model v3.2). Keyed by ``entry_id``.

Callers resolve ``investment_id`` via ``investment_repository.resolve_investment()``
before calling ``upsert_trade_log_entry`` -- this module is a pure repository over
the DDL's own column names and does not translate JSON source keys
(e.g. ``ticker`` -> ``investment_id``, ``totalCost`` -> ``total_cost``); that
translation is the migration script's job.

Note: the JSON source (``data/trade-log.json``) also carries an
``extendedHours`` field that has no corresponding column in the
``trade_log_entry`` DDL and is intentionally not persisted here.

``tv_order_id`` (Wave 4 Task 11 addition, via ``db_client.py``'s
``SCHEMA_EVOLUTIONS``) DOES have a column -- trading.ts's /modify,
/cancel, and /log/sync-from-tv routes match live TradingView orders
against a logged entry's tvOrderId, so dropping it would silently break
that reconciliation for every entry logged after cutover.
"""

import sqlite3

_COLUMNS = (
    "entry_id", "investment_id", "account_id", "action", "shares", "price",
    "total_cost", "order_type", "limit_price", "trade_date", "notes",
    "status", "source", "priority", "logged_at", "tv_order_id",
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


def list_filled_trades_since(conn: sqlite3.Connection, since_date: str) -> list[dict]:
    """Filled trades on or after ``since_date`` (YYYY-MM-DD), oldest first, with ``symbol``.

    Only ``filled`` rows are real executions: planned, submitted and cancelled
    entries are excluded so recent-trade context never counts an order that did
    not happen.
    """
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT t.*, i.symbol FROM trade_log_entry t "
        "JOIN investment i ON i.investment_id = t.investment_id "
        "WHERE lower(t.status) = 'filled' AND t.trade_date >= ? "
        "ORDER BY t.trade_date, t.logged_at, t.entry_id;",
        (since_date,),
    )
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
