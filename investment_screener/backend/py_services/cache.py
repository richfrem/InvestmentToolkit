#!/usr/bin/env python3
"""
cache.py - The one TTL cache for raw market-data fetches, stored in SQLite.

Purpose:
    Shared TTL cache: one entry per (key, data_class) in domain_model.sqlite's ``fetch_cache``
    table (fetch_cache_repository.py), never JSON files. Used by market_data.py, edgar_facts.py,
    fetch_financials.py and fetch_portfolio_heatmap.py. Callers pass --no-cache upstream to bypass
    reads (still writes, so a subsequent call is warm).

Layer:
    Backend / Python Services

Key Functions (Index):
    - cache_get()
    - cache_set()

Key Input Dependencies:
    domain_model.sqlite (fetch_cache table, migration 0011)
"""
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.fetch_cache_repository import get_cached, put_cached  # noqa: E402

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "domain_model.sqlite"

CACHE_TTL_SECONDS = {
    "quote": 900,          # 15 min
    "ohlcv": 86400,         # 24h
    "fundamentals": 86400,  # 24h
    "estimates": 86400,     # 24h — matches the TTL estimates rode on before it got its own cache key
    "edgar": 604800,        # 7d
    "financials": 3600,     # 1h  (fetch_financials.py)
    "info": 900,            # 15 min (fetch_portfolio_heatmap.py)
}


def _key(key: str) -> str:
    return "".join(c for c in key if c.isalnum() or c in ("-", "."))


# Retrieve a value from cache if it exists and hasn't expired
def cache_get(key: str, data_class: str) -> Optional[dict]:
    """Return the cached value for (key, data_class) if present and younger than its TTL, else None."""
    try:
        conn = initialize_db(str(DB_PATH))
    except Exception:
        return None
    try:
        hit = get_cached(conn, data_class, _key(key))
    finally:
        conn.close()
    if hit is None:
        return None
    payload, fetched_at = hit
    if time.time() - fetched_at > CACHE_TTL_SECONDS.get(data_class, 3600):
        return None
    return payload


# Store a value in the cache
def cache_set(key: str, data_class: str, value: dict) -> None:
    """Store a value for (key, data_class), replacing any previous entry."""
    conn = initialize_db(str(DB_PATH))
    try:
        put_cached(conn, data_class, _key(key), value, time.time())
    finally:
        conn.close()
