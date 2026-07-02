"""
cache.py (Python Service)
=====================================

Purpose:
    Shared TTL-based JSON file cache for market_data.py. One cache entry per
    (key, data_class) pair. Callers pass --no-cache upstream to bypass reads
    (still writes, so a subsequent call is warm).

Layer: Backend / Python Services / Data Layer
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


def _cache_path(key: str, data_class: str) -> Path:
    safe_key = "".join(c for c in key if c.isalnum() or c in ("-", "."))
    return CACHE_DIR / f"{data_class}_{safe_key}.json"


def cache_get(key: str, data_class: str) -> Optional[dict]:
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


def cache_set(key: str, data_class: str, value: dict) -> None:
    path = _cache_path(key, data_class)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(value, f)
