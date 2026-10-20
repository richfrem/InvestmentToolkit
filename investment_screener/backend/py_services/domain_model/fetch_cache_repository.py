"""fetch_cache_repository.py - all ``fetch_cache`` reads and writes.

Purpose:
    The only code that touches ``fetch_cache``: the short-lived cache of raw market-data fetches
    used by cache.py (and through it market_data.py, edgar_facts.py, fetch_financials.py and
    fetch_portfolio_heatmap.py). Expiry is the caller's (cache.CACHE_TTL_SECONDS).

Layer: Backend / Python Services / Data Persistence

Key Functions (Index):
    - get_cached(): (payload, fetched_at epoch seconds) or None
    - put_cached(): insert or replace one entry
"""
import json
import sqlite3
from typing import Any, Optional


def get_cached(conn: sqlite3.Connection, data_class: str, cache_key: str) -> Optional[tuple[Any, float]]:
    row = conn.execute(
        "SELECT payload_json, fetched_at FROM fetch_cache WHERE data_class = ? AND cache_key = ?;",
        (data_class, cache_key),
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0]), float(row[1])
    except (TypeError, ValueError):
        return None


def put_cached(conn: sqlite3.Connection, data_class: str, cache_key: str, payload: Any, fetched_at: float) -> None:
    conn.execute(
        "INSERT INTO fetch_cache (data_class, cache_key, fetched_at, payload_json) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(data_class, cache_key) DO UPDATE SET fetched_at = excluded.fetched_at, payload_json = excluded.payload_json;",
        (data_class, cache_key, fetched_at, json.dumps(payload, default=str)),
    )
    conn.commit()
