"""evolution_event_repository.py - all ``evolution_event`` reads and writes.

Purpose:
    The only code that touches the ``evolution_event`` table: evolution events (earnings
    catalysts, breaker overrides, rebalance executions, large price moves, dividends, forced
    exits) as whole records. The same (ticker, event_type, event_date) may be stored more than
    once when its details changed. TypeScript does not read this table.

Layer:
    Backend / Python Services / Data Persistence

Key Input Dependencies:
    - domain_model.sqlite at schema version 4 or later (``evolution_event`` table)

Key Functions (Index):
    - insert_event(): append one event record
    - list_events(): every event record, oldest first
    - list_events_with_seq(): (event_seq, record) pairs, oldest first
    - update_event(): replace the stored record for one event_seq
"""
import json
import sqlite3


def insert_event(conn: sqlite3.Connection, record: dict) -> int:
    """Append ``record`` and return its ``event_seq``.

    The record must carry ``event_id`` and a ``context`` with ``ticker``, ``event_type`` and
    ``event_date``.
    """
    context = record["context"]
    cursor = conn.execute(
        "INSERT INTO evolution_event (event_id, ticker, event_type, event_date, record_json) "
        "VALUES (?, ?, ?, ?, ?);",
        (record["event_id"], context["ticker"], context["event_type"], context["event_date"], json.dumps(record)),
    )
    conn.commit()
    return cursor.lastrowid


def list_events_with_seq(conn: sqlite3.Connection) -> list[tuple[int, dict]]:
    """(event_seq, record) pairs, oldest first."""
    rows = conn.execute("SELECT event_seq, record_json FROM evolution_event ORDER BY event_seq;").fetchall()
    return [(r[0], json.loads(r[1])) for r in rows]


def list_events(conn: sqlite3.Connection) -> list[dict]:
    """Every event record, oldest first."""
    return [record for _seq, record in list_events_with_seq(conn)]


def update_event(conn: sqlite3.Connection, event_seq: int, record: dict) -> None:
    """Replace the stored record for ``event_seq`` (used to fill in outcomes)."""
    conn.execute("UPDATE evolution_event SET record_json = ? WHERE event_seq = ?;", (json.dumps(record), event_seq))
    conn.commit()
