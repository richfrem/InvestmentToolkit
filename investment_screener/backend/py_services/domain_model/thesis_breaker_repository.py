"""thesis_breaker_repository.py - all ``thesis_breaker`` / ``thesis_breaker_state`` reads and writes.

Purpose:
    The only code that touches the two thesis breaker tables, and the one definition of the
    breaker vocabulary (metrics, operators, statuses). TypeScript counterpart:
    ``src/services/ThesisBreakerRepository.ts``.

Layer:
    Backend / Python Services / Data Persistence

Key Input Dependencies:
    - domain_model.sqlite at schema version 2 or later (``investment``, ``thesis_breaker``,
      ``thesis_breaker_state`` tables)

Breaker definitions and evaluated state cross this boundary in the dict shapes the
evaluator (``thesis_breakers.py``) and its consumers already use:

  definition  {id, type, metric?, operator, threshold, horizon?, note?,
               status?, statusSetAt?, reviewCadenceDays?}
  state       {ticker: {breakerId: {type, status, currentValue?, conditionMet?,
               currentStreak?, streakStartDate?, lastEvaluatedAt?, statusSetAt?,
               reviewCadenceDays?, daysSinceReview?, stale?}}}

``investment.thesis_breaker_status`` is a derived scalar (worst current status) and is
written only by ``replace_breaker_state``.

Key Functions (Index):
    - AUTO_METRICS, VALID_OPERATORS, VALID_STATUSES: the one shared vocabulary
    - validate_breaker(): errors for a definition dict
    - list_breakers(): definitions for one ticker (list) or every ticker (dict)
    - upsert_breaker(), delete_breaker(), set_manual_status()
    - replace_breaker_state(), list_breaker_state()
"""

import json
import sqlite3
from datetime import datetime, timezone

AUTO_METRICS = frozenset({
    "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
})
VALID_OPERATORS = frozenset({"<", "<=", ">", ">=", "==", "in"})
VALID_STATUSES = frozenset({"OK", "WATCHING", "TRIGGERED"})
_SEVERITY = {"OK": 0, "WATCHING": 1, "TRIGGERED": 2}


def validate_breaker(breaker: dict) -> list[str]:
    """Return human-readable errors for a breaker definition; empty when valid."""
    errors: list[str] = []
    if not breaker.get("id"):
        errors.append("breaker missing 'id'")
    if breaker.get("type") not in ("auto", "manual"):
        errors.append(f"breaker 'type' must be 'auto' or 'manual', got {breaker.get('type')!r}")
    if breaker.get("type") == "auto" and breaker.get("metric") not in AUTO_METRICS:
        errors.append(f"auto breaker 'metric' must be one of {sorted(AUTO_METRICS)}, got {breaker.get('metric')!r}")
    if breaker.get("operator") not in VALID_OPERATORS:
        errors.append(f"'operator' must be one of {sorted(VALID_OPERATORS)}, got {breaker.get('operator')!r}")
    if breaker.get("operator") == "in" and not isinstance(breaker.get("threshold"), list):
        errors.append("operator 'in' requires 'threshold' to be a list")
    if breaker.get("type") == "manual":
        errors.extend(_manual_breaker_errors(breaker))
    return errors


def _manual_breaker_errors(breaker: dict) -> list[str]:
    """Errors specific to manual breakers: hand-set status, its date and the review cadence."""
    errors: list[str] = []
    if breaker.get("status") not in VALID_STATUSES:
        errors.append(f"manual breaker 'status' must be one of {sorted(VALID_STATUSES)}, got {breaker.get('status')!r}")
    if not breaker.get("statusSetAt"):
        errors.append("manual breaker missing 'statusSetAt'")
    if not breaker.get("reviewCadenceDays"):
        errors.append("manual breaker missing 'reviewCadenceDays'")
    return errors


def _investment_id(conn: sqlite3.Connection, symbol: str) -> str:
    """Investment id."""
    row = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (symbol,)).fetchone()
    if row is None:
        raise ValueError(f"ticker '{symbol}' not found in domain_model.sqlite")
    return row[0]


def _dumps(value) -> str | None:
    """Dumps."""
    return None if value is None else json.dumps(value)


def _loads(text: str | None):
    """Loads."""
    return None if text is None else json.loads(text)


def _definition(row: sqlite3.Row) -> dict:
    """Definition."""
    out = {"id": row["breaker_id"], "type": row["breaker_type"]}
    if row["metric"] is not None:
        out["metric"] = row["metric"]
    out["operator"] = row["operator"]
    out["threshold"] = _loads(row["threshold_json"])
    if row["horizon_json"] is not None:
        out["horizon"] = _loads(row["horizon_json"])
    if row["note"] is not None:
        out["note"] = row["note"]
    if row["breaker_type"] == "manual":
        out["status"] = row["status"]
        out["statusSetAt"] = row["status_set_at"]
        out["reviewCadenceDays"] = row["review_cadence_days"]
    return out


def list_breakers(conn: sqlite3.Connection, symbol: str | None = None):
    """Breaker definitions: a list for ``symbol``, or ``{ticker: [definitions]}`` for every ticker."""
    conn.row_factory = sqlite3.Row
    sql = ("SELECT b.*, i.symbol AS symbol FROM thesis_breaker b "
           "JOIN investment i ON i.investment_id = b.investment_id")
    if symbol is not None:
        rows = conn.execute(sql + " WHERE i.symbol = ? ORDER BY b.rowid;", (symbol,)).fetchall()
        return [_definition(r) for r in rows]
    out: dict[str, list[dict]] = {}
    for r in conn.execute(sql + " ORDER BY i.symbol, b.rowid;").fetchall():
        out.setdefault(r["symbol"], []).append(_definition(r))
    return out


def upsert_breaker(conn: sqlite3.Connection, symbol: str, breaker: dict) -> None:
    """Insert or replace one breaker definition. Raises ValueError when invalid or the ticker is unknown."""
    errors = validate_breaker(breaker)
    if errors:
        raise ValueError(f"Invalid breaker: {'; '.join(errors)}")
    investment_id = _investment_id(conn, symbol)
    manual = breaker["type"] == "manual"
    conn.execute(
        "INSERT INTO thesis_breaker (breaker_id, investment_id, breaker_type, metric, operator, "
        "threshold_json, horizon_json, note, status, status_set_at, review_cadence_days, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (investment_id, breaker_id) DO UPDATE SET "
        "breaker_type = excluded.breaker_type, metric = excluded.metric, operator = excluded.operator, "
        "threshold_json = excluded.threshold_json, horizon_json = excluded.horizon_json, "
        "note = excluded.note, status = excluded.status, status_set_at = excluded.status_set_at, "
        "review_cadence_days = excluded.review_cadence_days;",
        (breaker["id"], investment_id, breaker["type"], breaker.get("metric"), breaker["operator"],
         _dumps(breaker.get("threshold")), _dumps(breaker.get("horizon")), breaker.get("note"),
         breaker["status"] if manual else None, breaker["statusSetAt"] if manual else None,
         breaker["reviewCadenceDays"] if manual else None,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def delete_breaker(conn: sqlite3.Connection, symbol: str, breaker_id: str) -> None:
    """Delete a breaker and its evaluated state. Raises ValueError when it does not exist."""
    investment_id = _investment_id(conn, symbol)
    exists = conn.execute("SELECT 1 FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?;",
                          (investment_id, breaker_id)).fetchone()
    if not exists:
        raise ValueError(f"breaker id '{breaker_id}' not found on {symbol}")
    conn.execute("DELETE FROM thesis_breaker_state WHERE investment_id = ? AND breaker_id = ?;",
                 (investment_id, breaker_id))
    conn.execute("DELETE FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?;",
                 (investment_id, breaker_id))
    _refresh_investment_status(conn)
    conn.commit()


def set_manual_status(conn: sqlite3.Connection, symbol: str, breaker_id: str, status: str,
                      note: str | None, today: str | None = None) -> None:
    """Set a manual breaker's status and date; a note is appended after a dated separator."""
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}, got {status!r}")
    investment_id = _investment_id(conn, symbol)
    row = conn.execute("SELECT breaker_type, note FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?;",
                       (investment_id, breaker_id)).fetchone()
    if row is None:
        raise ValueError(f"breaker id '{breaker_id}' not found on {symbol}")
    if row[0] != "manual":
        raise ValueError(f"breaker '{breaker_id}' is type '{row[0]}' — status can only be set on manual breakers")
    today = today or datetime.now(timezone.utc).date().isoformat()
    new_note = row[1]
    if note:
        new_note = f"{row[1]} | status update {today}: {note}" if row[1] else note
    conn.execute("UPDATE thesis_breaker SET status = ?, status_set_at = ?, note = ? "
                 "WHERE investment_id = ? AND breaker_id = ?;",
                 (status, today, new_note, investment_id, breaker_id))
    conn.commit()


def replace_breaker_state(conn: sqlite3.Connection, state: dict[str, dict[str, dict]]) -> None:
    """Replace every evaluated state row and re-derive ``investment.thesis_breaker_status``.

    Raises ValueError, writing nothing, when a state entry names a breaker with no definition.
    """
    rows = []
    for symbol, breakers in state.items():
        investment_id = _investment_id(conn, symbol)
        for breaker_id, e in breakers.items():
            if not conn.execute("SELECT 1 FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?;",
                                (investment_id, breaker_id)).fetchone():
                raise ValueError(f"breaker id '{breaker_id}' not found on {symbol}")
            stale = e.get("stale")
            met = e.get("conditionMet")
            rows.append((investment_id, breaker_id, e["status"], _dumps(e.get("currentValue")),
                         None if met is None else int(met), e.get("currentStreak"), e.get("streakStartDate"),
                         e.get("lastEvaluatedAt") or datetime.now(timezone.utc).isoformat(),
                         e.get("daysSinceReview"), None if stale is None else int(stale)))
    conn.execute("DELETE FROM thesis_breaker_state;")
    conn.executemany(
        "INSERT INTO thesis_breaker_state (investment_id, breaker_id, status, current_value_json, "
        "condition_met, current_streak, streak_start_date, last_evaluated_at, days_since_review, is_stale) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", rows)
    _refresh_investment_status(conn)
    conn.commit()


def _refresh_investment_status(conn: sqlite3.Connection) -> None:
    """Refresh investment status."""
    conn.execute("UPDATE investment SET thesis_breaker_status = NULL "
                 "WHERE thesis_breaker_status IS NOT NULL;")
    worst: dict[str, str] = {}
    for investment_id, status in conn.execute("SELECT investment_id, status FROM thesis_breaker_state;"):
        if _SEVERITY[status] >= _SEVERITY.get(worst.get(investment_id, "OK"), 0):
            worst[investment_id] = status
    conn.executemany("UPDATE investment SET thesis_breaker_status = ? WHERE investment_id = ?;",
                     [(s, i) for i, s in worst.items()])


def list_breaker_state(conn: sqlite3.Connection) -> dict[str, dict[str, dict]]:
    """Evaluated state as ``{ticker: {breakerId: entry}}`` in the evaluator's shape."""
    conn.row_factory = sqlite3.Row
    out: dict[str, dict[str, dict]] = {}
    for r in conn.execute(
        "SELECT s.*, i.symbol AS symbol, b.breaker_type AS breaker_type, b.status_set_at AS status_set_at, "
        "b.review_cadence_days AS review_cadence_days FROM thesis_breaker_state s "
        "JOIN investment i ON i.investment_id = s.investment_id "
        "JOIN thesis_breaker b ON b.investment_id = s.investment_id AND b.breaker_id = s.breaker_id "
        "ORDER BY i.symbol, b.rowid;"
    ).fetchall():
        if r["breaker_type"] == "auto":
            entry = {"type": "auto", "currentValue": _loads(r["current_value_json"]),
                     "conditionMet": None if r["condition_met"] is None else bool(r["condition_met"]),
                     "currentStreak": r["current_streak"], "streakStartDate": r["streak_start_date"],
                     "lastEvaluatedAt": r["last_evaluated_at"], "status": r["status"]}
        else:
            entry = {"type": "manual", "status": r["status"], "statusSetAt": r["status_set_at"],
                     "reviewCadenceDays": r["review_cadence_days"], "daysSinceReview": r["days_since_review"],
                     "stale": None if r["is_stale"] is None else bool(r["is_stale"])}
        out.setdefault(r["symbol"], {})[r["breaker_id"]] = entry
    return out
