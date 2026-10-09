"""All ``portfolio_change_log`` table reads and writes live here.

Portfolio-wide version history ({version, date, note} per entry) -- append-only, never
overwrite/replace an existing entry.
"""

import sqlite3
import uuid
from datetime import datetime, timezone


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


def record_change(conn: sqlite3.Connection, note: str) -> str:
    """Append a change-log entry numbered ``MAX(version) + 1`` and return its ``entry_id``.

    The one function every state-changing target edit calls. Versions that are not whole
    numbers (for example ``9.6``) count by their integer part. Raises ValueError for a blank note.
    """
    if not note or not note.strip():
        raise ValueError("a change-log note is required")
    row = conn.execute("SELECT MAX(CAST(version AS INTEGER)) FROM portfolio_change_log;").fetchone()
    version = str((row[0] or 0) + 1)
    now = datetime.now(timezone.utc)
    return add_change_log_entry(conn, version, now.date().isoformat(), note.strip(),
                                now.isoformat().replace("+00:00", "Z"))
