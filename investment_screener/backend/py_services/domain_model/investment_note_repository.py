"""All ``investment_note`` table reads and writes live here.

Append-only -- this table exists specifically to fix the "un-queryable history"
problem of agentRationale being a single hand-concatenated string (spec s2.3).
Never overwrite/replace an existing note row.
"""

import sqlite3
import uuid


def add_note(
    conn: sqlite3.Connection,
    investment_id: str,
    note_date: str,
    body: str,
    note_type: str = "AGENT_RATIONALE",
    source: str | None = None,
) -> str:
    note_id = f"{investment_id}-note-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO investment_note "
        "(note_id, investment_id, note_date, note_type, body, source) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (note_id, investment_id, note_date, note_type, body, source),
    )
    conn.commit()
    return note_id


def list_notes(conn: sqlite3.Connection, investment_id: str) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM investment_note WHERE investment_id = ? ORDER BY note_date ASC;",
        (investment_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_latest_note(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM investment_note WHERE investment_id = ? "
        "ORDER BY note_date DESC LIMIT 1;",
        (investment_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None
