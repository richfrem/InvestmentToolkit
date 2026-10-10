"""computed_snapshot_repository.py - all ``computed_snapshot`` reads and writes.

Purpose:
    The only code that touches the ``computed_snapshot`` table: computed results (risk
    snapshot, rebalance plan, market regime, risk officer review and overrides) that a later
    step reads back. TypeScript does not read this table.

Layer:
    Backend / Python Services / Data Persistence

Key Input Dependencies:
    - domain_model.sqlite at schema version 3 or later (``computed_snapshot`` table)

Key Functions (Index):
    - SNAPSHOT_NAMES: the allowed snapshot names
    - save_snapshot(): append one result and prune history
    - load_latest_snapshot(): newest payload for a name, or None
    - load_latest_snapshot_with_time(): (payload, computed_at) for the newest row, or None
    - list_snapshots(): every kept payload for a name, oldest first
"""
import json
import sqlite3
from datetime import datetime, timezone

SNAPSHOT_NAMES = frozenset({
    "risk_snapshot", "rebalance_plan", "market_regime",
    "risk_officer_review", "risk_officer_override",
})
KEEP_PER_NAME = 30


def _check_name(name: str) -> None:
    if name not in SNAPSHOT_NAMES:
        raise ValueError(f"unknown snapshot name {name!r}; expected one of {sorted(SNAPSHOT_NAMES)}")


def save_snapshot(
    conn: sqlite3.Connection, name: str, payload: dict, computed_at: str | None = None,
    keep: int = KEEP_PER_NAME,
) -> int:
    """Append ``payload`` as the newest ``name`` snapshot, keep the last ``keep`` rows, return its id."""
    _check_name(name)
    stamp = computed_at or datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO computed_snapshot (snapshot_name, computed_at, payload_json) VALUES (?, ?, ?);",
        (name, stamp, json.dumps(payload)),
    )
    conn.execute(
        "DELETE FROM computed_snapshot WHERE snapshot_name = ? AND snapshot_id NOT IN ("
        "SELECT snapshot_id FROM computed_snapshot WHERE snapshot_name = ? "
        "ORDER BY computed_at DESC, snapshot_id DESC LIMIT ?);",
        (name, name, keep),
    )
    conn.commit()
    return cursor.lastrowid


def load_latest_snapshot_with_time(conn: sqlite3.Connection, name: str) -> tuple[dict, str] | None:
    """(payload, computed_at) of the newest ``name`` snapshot, or None when there is none."""
    _check_name(name)
    row = conn.execute(
        "SELECT payload_json, computed_at FROM computed_snapshot WHERE snapshot_name = ? "
        "ORDER BY computed_at DESC, snapshot_id DESC LIMIT 1;",
        (name,),
    ).fetchone()
    return (json.loads(row[0]), row[1]) if row else None


def load_latest_snapshot(conn: sqlite3.Connection, name: str) -> dict | None:
    """Payload of the newest ``name`` snapshot, or None when there is none."""
    found = load_latest_snapshot_with_time(conn, name)
    return found[0] if found else None


def list_snapshots(conn: sqlite3.Connection, name: str) -> list[dict]:
    """Every kept ``name`` payload, oldest first."""
    _check_name(name)
    rows = conn.execute(
        "SELECT payload_json FROM computed_snapshot WHERE snapshot_name = ? "
        "ORDER BY computed_at ASC, snapshot_id ASC;",
        (name,),
    ).fetchall()
    return [json.loads(r[0]) for r in rows]
