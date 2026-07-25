"""All ``portfolio_change_log`` table reads and writes live here.

Portfolio-wide version history (target-portfolio.json's former top-level
``changeLog`` array: {version, date, note} per entry) -- append-only, never
overwrite/replace an existing entry.
"""

import sqlite3
import uuid


def add_change_log_entry(
    conn: sqlite3.Connection,
    version: str,
    entry_date: str,
    note: str,
    created_at: str,
) -> str:
    entry_id = f"changelog-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO portfolio_change_log "
        "(entry_id, version, entry_date, note, created_at) "
        "VALUES (?, ?, ?, ?, ?);",
        (entry_id, version, entry_date, note, created_at),
    )
    conn.commit()
    return entry_id


def list_change_log(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM portfolio_change_log ORDER BY entry_date ASC, created_at ASC;"
    )
    return [dict(row) for row in cursor.fetchall()]
