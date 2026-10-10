"""valuation_workpaper_repository.py - all ``valuation_workpaper`` reads and writes.

Purpose:
    The only code that touches the ``valuation_workpaper`` table: the working documents of a stock
    valuation run (raw fundamentals, scenarios, DCF result, WACC build, reverse DCF, technicals,
    intake, projection payload, ...), keyed by (symbol, stage). They replace the per-stock JSON
    files that used to sit in temp/evaluations. Identical content for the same symbol and stage
    is stored once.

Layer:
    Backend / Python Services / Data Persistence

Key Input Dependencies:
    - domain_model.sqlite at schema version 6 or later (``valuation_workpaper`` table)

Key Functions (Index):
    - put_workpaper(): store one document; returns (workpaper_id, created)
    - get_latest_workpaper(): newest payload for a symbol and stage, or None
    - list_workpapers(): metadata rows (no payload), newest first
    - list_stages(): the stages stored for a symbol
"""
import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone


def _digest(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def put_workpaper(
    conn: sqlite3.Connection, symbol: str, stage: str, payload, as_of: str | None = None, source: str | None = None
) -> tuple[int, bool]:
    """Store ``payload`` for (symbol, stage); returns (workpaper_id, created).

    ``created`` is False when the same content is already stored for that symbol and stage.
    """
    symbol = symbol.upper()
    digest = _digest(payload)
    existing = conn.execute(
        "SELECT workpaper_id FROM valuation_workpaper WHERE symbol = ? AND stage = ? AND content_hash = ?;",
        (symbol, stage, digest),
    ).fetchone()
    if existing:
        return existing[0], False
    cursor = conn.execute(
        "INSERT INTO valuation_workpaper (symbol, stage, as_of, content_hash, payload_json, source, saved_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?);",
        (symbol, stage, as_of or date.today().isoformat(), digest, json.dumps(payload), source,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cursor.lastrowid, True


def get_latest_workpaper(conn: sqlite3.Connection, symbol: str, stage: str):
    """The newest payload stored for (symbol, stage), or None."""
    row = conn.execute(
        "SELECT payload_json FROM valuation_workpaper WHERE symbol = ? AND stage = ? "
        "ORDER BY as_of DESC, workpaper_id DESC LIMIT 1;",
        (symbol.upper(), stage),
    ).fetchone()
    return json.loads(row[0]) if row else None


def list_workpapers(conn: sqlite3.Connection, symbol: str | None = None, stage: str | None = None) -> list[dict]:
    """Metadata (id, symbol, stage, as_of, source, saved_at) for matching rows, newest first."""
    where, params = [], []
    if symbol:
        where.append("symbol = ?")
        params.append(symbol.upper())
    if stage:
        where.append("stage = ?")
        params.append(stage)
    sql = "SELECT workpaper_id, symbol, stage, as_of, source, saved_at FROM valuation_workpaper"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY as_of DESC, workpaper_id DESC;"
    cols = ("workpaper_id", "symbol", "stage", "as_of", "source", "saved_at")
    return [dict(zip(cols, r)) for r in conn.execute(sql, params).fetchall()]


def list_stages(conn: sqlite3.Connection, symbol: str) -> list[str]:
    """The distinct stages stored for ``symbol``, alphabetical."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT stage FROM valuation_workpaper WHERE symbol = ? ORDER BY stage;", (symbol.upper(),)
    ).fetchall()]
