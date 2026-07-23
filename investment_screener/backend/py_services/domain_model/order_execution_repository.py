"""All ``order_execution`` table reads and writes live here. This table mirrors
the append-only ``orders_executed.jsonl`` log written by ``order_risk_gates.py``
(``log_order_execution``). The JSONL source has no stable id -- the caller
(migration script, or a future producer cutover) is responsible for generating
``execution_id`` and resolving ``investment_id`` via
``investment_repository.resolve_investment()`` before calling this module.

JSON-blob column convention: like ``alert_repository.condition_json`` and
``projection_repository.snapshot_json``, ``gate_result_json`` is accepted here
as an already-serialized string. This module never calls ``json.dumps`` --
the caller serializes the gate_result dict before passing it in.

Append-only semantics: in real producer usage a given ``execution_id`` is
never re-used (every order execution is logged exactly once, with a new id).
However the migration script that backfills this table from
``orders_executed.jsonl`` must be safely re-runnable without duplicating
rows, so ``insert_order_execution`` uses the same idempotent
``INSERT ... ON CONFLICT DO UPDATE`` upsert pattern as every other repository
in this directory, even though a genuine second call with the same id is not
expected to occur outside of a migration re-run.
"""

import sqlite3


def insert_order_execution(conn: sqlite3.Connection, execution: dict) -> str:
    """Insert (or idempotently update) a single order execution record.

    Args:
        conn: Open SQLite connection.
        execution: Dict keyed by DDL column names: execution_id, executed_at,
            investment_id, side, shares, price, decision, gate_result_json.
            ``gate_result_json`` must already be a JSON string (or None) --
            this function does not serialize it.

    Returns:
        The execution_id of the inserted/updated row.
    """
    conn.execute(
        "INSERT INTO order_execution "
        "(execution_id, executed_at, investment_id, side, shares, price, "
        "decision, gate_result_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(execution_id) DO UPDATE SET "
        "executed_at=excluded.executed_at, investment_id=excluded.investment_id, "
        "side=excluded.side, shares=excluded.shares, price=excluded.price, "
        "decision=excluded.decision, gate_result_json=excluded.gate_result_json;",
        (
            execution["execution_id"],
            execution["executed_at"],
            execution["investment_id"],
            execution.get("side"),
            execution.get("shares"),
            execution.get("price"),
            execution.get("decision"),
            execution.get("gate_result_json"),
        ),
    )
    conn.commit()
    return execution["execution_id"]


def list_order_executions(
    conn: sqlite3.Connection,
    investment_id: str | None = None,
) -> list[dict]:
    """List order executions, optionally filtered by investment_id.

    Args:
        conn: Open SQLite connection.
        investment_id: If provided, restrict results to this investment.

    Returns:
        List of row dicts ordered by executed_at.
    """
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM order_execution WHERE 1=1"
    params: list = []
    if investment_id:
        query += " AND investment_id = ?"
        params.append(investment_id)
    query += " ORDER BY executed_at"
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
