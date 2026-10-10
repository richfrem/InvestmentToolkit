"""thesis_document_member_repository.py - all ``thesis_document_member`` reads and writes.

Purpose:
    The only code that touches the ``thesis_document_member`` table: which stocks each thesis
    document (a sub-strategy markdown file under data/theses/sub_strategies) covers. The web
    app uses it to show the live positions table for one thesis. A stock can belong to several
    documents.

Layer:
    Backend / Python Services / Data Persistence

Key Input Dependencies:
    - domain_model.sqlite at schema version 7 or later (``thesis_document_member`` table)

Key Functions (Index):
    - replace_members(): set the full member list of one document
    - list_members(): {symbol: [document_id, ...]} across all documents
"""
import sqlite3
from datetime import datetime, timezone


def replace_members(conn: sqlite3.Connection, document_id: str, symbols: list[str]) -> int:
    """Make ``symbols`` the complete member list of ``document_id``; returns how many were stored."""
    now = datetime.now(timezone.utc).isoformat()
    unique = sorted({s.strip().upper() for s in symbols if s and s.strip()})
    conn.execute("DELETE FROM thesis_document_member WHERE document_id = ?;", (document_id,))
    conn.executemany(
        "INSERT INTO thesis_document_member (document_id, symbol, added_at) VALUES (?, ?, ?);",
        [(document_id, s, now) for s in unique],
    )
    conn.commit()
    return len(unique)


def list_members(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Every stock's documents: {symbol: [document_id, ...]}, both sorted."""
    out: dict[str, list[str]] = {}
    for symbol, document_id in conn.execute(
        "SELECT symbol, document_id FROM thesis_document_member ORDER BY symbol, document_id;"
    ):
        out.setdefault(symbol, []).append(document_id)
    return out
