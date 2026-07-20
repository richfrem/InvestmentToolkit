"""All ``alert`` table reads and writes live here. TradingView is the upstream
authority; this table is the local synced mirror (spec s2.7 -- same "sync mirror"
reasoning as broker holdings, NOT a bare RETAIN_AS_EXTERNAL_CACHE exception)."""

import sqlite3


def upsert_alert(
    conn: sqlite3.Connection,
    alert_id: str,
    investment_id: str | None,
    alert_type: str | None,
    message: str | None,
    price: float | None,
    condition_json: str | None,
    active: bool,
    resolution: str | None,
    created_at: str | None,
    last_fired_at: str | None,
    expiration_at: str | None,
    synced_at: str,
) -> str:
    conn.execute(
        "INSERT INTO alert "
        "(alert_id, investment_id, alert_type, message, price, condition_json, "
        "active, resolution, created_at, last_fired_at, expiration_at, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(alert_id) DO UPDATE SET "
        "investment_id=excluded.investment_id, alert_type=excluded.alert_type, "
        "message=excluded.message, price=excluded.price, "
        "condition_json=excluded.condition_json, active=excluded.active, "
        "resolution=excluded.resolution, last_fired_at=excluded.last_fired_at, "
        "expiration_at=excluded.expiration_at, synced_at=excluded.synced_at;",
        (alert_id, investment_id, alert_type, message, price, condition_json,
         int(active), resolution, created_at, last_fired_at, expiration_at, synced_at),
    )
    conn.commit()
    return alert_id


def list_alerts(
    conn: sqlite3.Connection,
    investment_id: str | None = None,
    active_only: bool = False,
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM alert WHERE 1=1"
    params: list = []
    if investment_id:
        query += " AND investment_id = ?"
        params.append(investment_id)
    if active_only:
        query += " AND active = 1"
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
