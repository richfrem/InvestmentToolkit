"""All ``account`` table reads and writes live here (ADR-029 anti-duplication rule)."""

import sqlite3


def upsert_account(
    conn: sqlite3.Connection,
    account_id: str,
    account_name: str,
    account_type: str,
    base_currency: str = "CAD",
) -> None:
    conn.execute(
        "INSERT INTO account (account_id, account_name, account_type, base_currency) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(account_id) DO UPDATE SET "
        "account_name=excluded.account_name, account_type=excluded.account_type, "
        "base_currency=excluded.base_currency;",
        (account_id, account_name, account_type, base_currency),
    )
    conn.commit()


def get_account(conn: sqlite3.Connection, account_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM account WHERE account_id = ?;", (account_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_accounts(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM account;")
    return [dict(row) for row in cursor.fetchall()]
