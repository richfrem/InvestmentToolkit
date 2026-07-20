"""All ``strategy_pillar``/``sub_strategy`` table reads and writes live here
(ADR-029 anti-duplication rule, same as investment_repository.py/account_repository.py)."""

import sqlite3


def resolve_pillar(
    conn: sqlite3.Connection,
    pillar_id: str,
    name: str,
    target_weight: float | None = None,
) -> str:
    conn.execute(
        "INSERT INTO strategy_pillar (pillar_id, name, target_weight) VALUES (?, ?, ?) "
        "ON CONFLICT(pillar_id) DO UPDATE SET name=excluded.name, "
        "target_weight=excluded.target_weight;",
        (pillar_id, name, target_weight),
    )
    conn.commit()
    return pillar_id


def resolve_sub_strategy(
    conn: sqlite3.Connection,
    sub_strategy_id: str,
    pillar_id: str,
    name: str,
) -> str:
    conn.execute(
        "INSERT INTO sub_strategy (sub_strategy_id, pillar_id, name) VALUES (?, ?, ?) "
        "ON CONFLICT(sub_strategy_id) DO UPDATE SET pillar_id=excluded.pillar_id, "
        "name=excluded.name;",
        (sub_strategy_id, pillar_id, name),
    )
    conn.commit()
    return sub_strategy_id


def list_pillars(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM strategy_pillar;")
    return [dict(row) for row in cursor.fetchall()]


def list_sub_strategies(
    conn: sqlite3.Connection, pillar_id: str | None = None
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    if pillar_id:
        cursor = conn.execute(
            "SELECT * FROM sub_strategy WHERE pillar_id = ?;", (pillar_id,)
        )
    else:
        cursor = conn.execute("SELECT * FROM sub_strategy;")
    return [dict(row) for row in cursor.fetchall()]
