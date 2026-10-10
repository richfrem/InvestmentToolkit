"""thesis_document_currency_repository.py - all ``thesis_document_currency`` reads and writes.

Purpose:
    The only code that touches the ``thesis_document_currency`` table: one current
    "developments" note per thesis document, replaced on each refresh (no history; the events
    behind a note stay in the intelligence ledger).

Layer:
    Backend / Python Services / Data Persistence

Key Input Dependencies:
    - domain_model.sqlite at schema version 8 or later (``thesis_document_currency`` table)

Key Functions (Index):
    - put_currency(): insert or replace the note of one document
    - touch_currency(): re-date an existing note without changing its text
    - get_currency(): the note of one document, or None
    - list_currency(): every document's note metadata
"""
import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    """UTC time in the ledger's own format (second precision, trailing Z) so the two compare as strings."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def put_currency(conn: sqlite3.Connection, document_id: str, as_of: str, markdown: str, updated_by: str | None = None) -> None:
    """Make ``markdown`` the one current note of ``document_id``, dated ``as_of``."""
    conn.execute(
        "INSERT INTO thesis_document_currency (document_id, as_of, markdown, updated_at, updated_by) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(document_id) DO UPDATE SET "
        "as_of = excluded.as_of, markdown = excluded.markdown, updated_at = excluded.updated_at, updated_by = excluded.updated_by;",
        (document_id, as_of, markdown, _now(), updated_by),
    )
    conn.commit()


def touch_currency(conn: sqlite3.Connection, document_id: str, as_of: str, updated_by: str | None = None) -> bool:
    """Re-date an existing note (nothing material changed); False when the document has no note yet."""
    cursor = conn.execute(
        "UPDATE thesis_document_currency SET as_of = ?, updated_at = ?, updated_by = ? WHERE document_id = ?;",
        (as_of, _now(), updated_by, document_id),
    )
    conn.commit()
    return cursor.rowcount == 1


def get_currency(conn: sqlite3.Connection, document_id: str) -> dict | None:
    """{document_id, as_of, markdown, updated_at, updated_by} or None."""
    row = conn.execute(
        "SELECT document_id, as_of, markdown, updated_at, updated_by FROM thesis_document_currency WHERE document_id = ?;",
        (document_id,),
    ).fetchone()
    return dict(zip(("document_id", "as_of", "markdown", "updated_at", "updated_by"), row)) if row else None


def list_currency(conn: sqlite3.Connection) -> dict[str, dict]:
    """{document_id: {as_of, updated_at, updated_by}} for every document that has a note."""
    return {
        r[0]: {"as_of": r[1], "updated_at": r[2], "updated_by": r[3]}
        for r in conn.execute("SELECT document_id, as_of, updated_at, updated_by FROM thesis_document_currency;")
    }
