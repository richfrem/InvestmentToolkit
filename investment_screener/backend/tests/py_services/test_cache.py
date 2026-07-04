import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from cache import cache_get, cache_set, CACHE_TTL_SECONDS  # noqa: E402


def test_cache_set_then_get_returns_the_value(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    cache_set("AAPL", "quote", {"price": 200.0})
    result = cache_get("AAPL", "quote")
    assert result == {"price": 200.0}


def test_cache_get_returns_none_when_key_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    assert cache_get("MISSING", "quote") is None


def test_cache_get_returns_none_when_entry_is_older_than_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    cache_set("AAPL", "quote", {"price": 200.0})
    # quote TTL is 900s — simulate an entry written 1000s ago
    cache_file = tmp_path / "quote_AAPL.json"
    old_time = time.time() - 1000
    import os
    os.utime(cache_file, (old_time, old_time))
    assert cache_get("AAPL", "quote") is None


def test_cache_ttl_seconds_has_all_four_data_classes():
    assert CACHE_TTL_SECONDS["quote"] == 900
    assert CACHE_TTL_SECONDS["ohlcv"] == 86400
    assert CACHE_TTL_SECONDS["fundamentals"] == 86400
    assert CACHE_TTL_SECONDS["edgar"] == 604800


def test_cache_set_creates_cache_dir_if_missing(tmp_path, monkeypatch):
    target_dir = tmp_path / "nested" / "cache"
    monkeypatch.setattr("cache.CACHE_DIR", target_dir)
    cache_set("AAPL", "quote", {"price": 200.0})
    assert target_dir.exists()
