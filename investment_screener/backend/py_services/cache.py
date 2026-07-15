#!/usr/bin/env python3
"""
cache.py - Python utility script.

Purpose:
    Shared TTL-based JSON file cache for market_data.py. One cache entry per
    (key, data_class) pair. Callers pass --no-cache upstream to bypass reads
    (still writes, so a subsequent call is warm).

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - _cache_path()
    - cache_get()
    - cache_set()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import json
import os
import time
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data" / "cache"

CACHE_TTL_SECONDS = {
    "quote": 900,          # 15 min
    "ohlcv": 86400,         # 24h
    "fundamentals": 86400,  # 24h
    "edgar": 604800,        # 7d
}


# Construct a cache file path from key and data class
def _cache_path(key: str, data_class: str) -> Path:
    """Construct a cache file path from key and data class.

    Args:
        key: Cache key, sanitized to alphanumeric + '-' + '.'.
        data_class: Data class name (e.g., 'quote', 'ohlcv').

    Returns:
        Path object pointing to the cache file.
    """
    safe_key = "".join(c for c in key if c.isalnum() or c in ("-", "."))
    return CACHE_DIR / f"{data_class}_{safe_key}.json"


# Retrieve a value from cache if it exists and hasn't expired
def cache_get(key: str, data_class: str) -> Optional[dict]:
    """Retrieve a value from cache if it exists and hasn't expired.

    Args:
        key: Cache key.
        data_class: Data class name to look up TTL.

    Returns:
        Cached dict if found and not expired; None otherwise.
    """
    path = _cache_path(key, data_class)
    if not path.exists():
        return None
    ttl = CACHE_TTL_SECONDS.get(data_class, 3600)
    age = time.time() - os.path.getmtime(path)
    if age > ttl:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# Store a value in the cache
def cache_set(key: str, data_class: str, value: dict) -> None:
    """Store a value in the cache.

    Args:
        key: Cache key.
        data_class: Data class name.
        value: Dict to cache.
    """
    path = _cache_path(key, data_class)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(value, f)
