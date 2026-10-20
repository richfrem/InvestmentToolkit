import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from cache import cache_get, cache_set, CACHE_TTL_SECONDS  # noqa: E402


def test_cache_set_then_get_returns_the_value(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.DB_PATH", tmp_path / "cache.sqlite")
    cache_set("AAPL", "quote", {"price": 200.0})
    result = cache_get("AAPL", "quote")
    assert result == {"price": 200.0}


def test_cache_get_returns_none_when_key_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.DB_PATH", tmp_path / "cache.sqlite")
    assert cache_get("MISSING", "quote") is None


def test_cache_get_returns_none_when_entry_is_older_than_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.DB_PATH", tmp_path / "cache.sqlite")
    real_time = time.time
    monkeypatch.setattr("cache.time.time", lambda: real_time() - 1000)   # written 1000s ago
    cache_set("AAPL", "quote", {"price": 200.0})
    monkeypatch.setattr("cache.time.time", real_time)
    assert cache_get("AAPL", "quote") is None                              # quote TTL is 900s


def test_cache_ttl_seconds_has_all_four_data_classes():
    assert CACHE_TTL_SECONDS["quote"] == 900
    assert CACHE_TTL_SECONDS["ohlcv"] == 86400
    assert CACHE_TTL_SECONDS["fundamentals"] == 86400
    assert CACHE_TTL_SECONDS["edgar"] == 604800


def test_cache_writes_sqlite_rows_never_json_files(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "cache.sqlite"
    monkeypatch.setattr("cache.DB_PATH", db)
    cache_set("AAPL", "quote", {"price": 200.0})
    cache_set("AAPL", "quote", {"price": 201.0})   # overwrite, not a second row
    rows = sqlite3.connect(db).execute("SELECT data_class, cache_key FROM fetch_cache").fetchall()
    assert rows == [("quote", "AAPL")]
    assert cache_get("AAPL", "quote") == {"price": 201.0}
    assert list(tmp_path.glob("*.json")) == []
