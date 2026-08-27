"""All ``account_investment`` table reads and writes live here (ADR-029 anti-duplication rule)."""

import sqlite3


def upsert_account_investment(
    conn: sqlite3.Connection,
    account_id: str,
    investment_id: str,
    quantity: float,
    average_cost: float | None,
    book_value: float | None,
    currency: str,
    last_synced_at: str,
) -> str:
    account_investment_id = f"{account_id}:{investment_id}"
    conn.execute(
        "INSERT INTO account_investment "
        "(account_investment_id, account_id, investment_id, quantity, average_cost, "
        "book_value, currency, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(account_id, investment_id) DO UPDATE SET "
        "quantity=excluded.quantity, average_cost=excluded.average_cost, "
        "book_value=excluded.book_value, currency=excluded.currency, "
        "last_synced_at=excluded.last_synced_at;",
        (
            account_investment_id, account_id, investment_id, quantity,
            average_cost, book_value, currency, last_synced_at,
        ),
    )
    conn.commit()
    return account_investment_id


def delete_stale_account_investments(
    conn: sqlite3.Connection,
    account_id: str,
    keep_investment_ids: set[str],
) -> int:
    """Remove account_investment rows for account_id no longer present in a full sync.

    A broker sync (TradingView or Questrade) reports the complete current holding
    set for an account each time. Any investment_id previously recorded for that
    account but absent from keep_investment_ids has been fully sold/closed and
    must be removed — leaving it would silently overstate holdings (stale entry).

    Returns:
        Number of stale rows deleted.
    """
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT investment_id FROM account_investment WHERE account_id = ?",
            (account_id,),
        ).fetchall()
    }
    stale = existing - keep_investment_ids
    for investment_id in stale:
        conn.execute(
            "DELETE FROM account_investment WHERE account_id = ? AND investment_id = ?",
            (account_id, investment_id),
        )
    if stale:
        conn.commit()
    return len(stale)


def list_account_investments(
    conn: sqlite3.Connection,
    account_id: str | None = None,
    investment_id: str | None = None,
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM account_investment WHERE 1=1"
    params: list[str] = []
    if account_id:
        query += " AND account_id = ?"
        params.append(account_id)
    if investment_id:
        query += " AND investment_id = ?"
        params.append(investment_id)
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
