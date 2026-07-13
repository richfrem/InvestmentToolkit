"""
Task 5A-7: Cache Last-Known-Good

Tests for tv_cdp_health.py cache_get() / cache_set() / cache_clear() /
generate_cache_key() functions. Verifies file-based JSONL caching of TV
CDP responses with per-entry TTL, lazy expiration (removed only on
access, not proactively), atomic rewrites, and deterministic key
generation.

IMPORTANT: All tests monkeypatch the module-level TV_CDP_CACHE_PATH
constant to a pytest tmp_path location. None of these tests may write to
the real investment_screener/backend/data/tv_cdp_responses_cache.jsonl
path.

IMPORTANT: TTL expiry is simulated by monkeypatching tv_cdp_health.time.time
(the module's imported `time` object), never by a real time.sleep(). This
keeps the suite fast and deterministic — see feedback from 5A-2/5A-3 fix
rounds where real sleeps caused flaky, slow tests.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import tv_cdp_health  # noqa: E402
from tv_cdp_health import cache_get, cache_set, cache_clear, generate_cache_key  # noqa: E402


@pytest.fixture
def cache_path(tmp_path, monkeypatch):
    """Point TV_CDP_CACHE_PATH at a temp file for the duration of a test."""
    path = tmp_path / "tv_cdp_responses_cache.jsonl"
    monkeypatch.setattr(tv_cdp_health, "TV_CDP_CACHE_PATH", path)
    return path


@pytest.fixture
def fake_clock(monkeypatch):
    """
    Replace tv_cdp_health.time.time with a controllable fake clock.

    Returns a small object with a `.now` attribute (float, seconds) that
    tests can mutate directly to simulate elapsed wall-clock time without
    ever sleeping for real.
    """
    class FakeClock:
        now = 1_000_000.0

        def time(self):
            return self.now

    clock = FakeClock()
    monkeypatch.setattr(tv_cdp_health.time, "time", clock.time)
    return clock


def _read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- Test 1: cache_set stores response ---

def test_cache_set_stores_response(cache_path, fake_clock):
    """Calling cache_set writes a matching entry to the cache file."""
    cache_set("quote:AAPL", {"price": 123.45}, ttl_seconds=300)

    lines = _read_lines(cache_path)

    assert len(lines) == 1
    assert lines[0]["key"] == "quote:AAPL"
    assert lines[0]["response"] == {"price": 123.45}
    assert lines[0]["ttl_seconds"] == 300
    assert "timestamp" in lines[0]


# --- Test 2: cache_get returns fresh response ---

def test_cache_get_returns_fresh_response(cache_path, fake_clock):
    """Set then immediately get (no time elapsed) returns the stored response."""
    cache_set("quote:AAPL", {"price": 123.45}, ttl_seconds=300)

    result = cache_get("quote:AAPL")

    assert result == {"price": 123.45}


# --- Test 3: cache_get returns None on expired TTL (no real sleep) ---

def test_cache_get_returns_none_on_expired_ttl(cache_path, fake_clock):
    """
    Set cache with a 1s TTL, advance the fake clock by 2s (no real sleep),
    then get — expect None because the entry has expired.
    """
    cache_set("quote:AAPL", {"price": 123.45}, ttl_seconds=1)

    fake_clock.now += 2  # simulate 2 seconds elapsing, instantly

    result = cache_get("quote:AAPL")

    assert result is None


# --- Test 4: cache_get removes expired entry from the file (lazy expiration) ---

def test_cache_get_removes_expired_entry(cache_path, fake_clock):
    """Accessing an expired entry cleans it out of the cache file (lazy expiration)."""
    cache_set("quote:AAPL", {"price": 123.45}, ttl_seconds=1)
    fake_clock.now += 2

    cache_get("quote:AAPL")

    lines = _read_lines(cache_path)
    assert lines == []


def test_cache_not_proactively_expired_before_access(cache_path, fake_clock):
    """
    Lazy expiration: an expired entry stays in the file until it is
    actually accessed via cache_get — nothing sweeps it out proactively.
    """
    cache_set("quote:AAPL", {"price": 123.45}, ttl_seconds=1)
    fake_clock.now += 2

    # No cache_get call yet — entry should still be physically present.
    lines = _read_lines(cache_path)
    assert len(lines) == 1
    assert lines[0]["key"] == "quote:AAPL"


# --- Test 5: cache_clear removes all entries ---

def test_cache_clear_removes_all_entries(cache_path, fake_clock):
    """Setting multiple entries then cache_clear() leaves the cache empty."""
    cache_set("quote:AAPL", {"price": 1}, ttl_seconds=300)
    cache_set("quote:TSLA", {"price": 2}, ttl_seconds=300)

    cache_clear()

    lines = _read_lines(cache_path)
    assert lines == []


def test_cache_clear_is_noop_when_no_cache_file(cache_path, fake_clock):
    """cache_clear() on a nonexistent cache file does not raise."""
    assert not cache_path.exists()

    cache_clear()  # must not raise

    assert not cache_path.exists()


# --- Test 6: cache key generation is deterministic ---

def test_cache_key_generation_deterministic(fake_clock):
    """Same function name + args always produce the identical cache key."""
    key1 = generate_cache_key("quote", {"symbol": "AAPL", "timeframe": "1D"})
    key2 = generate_cache_key("quote", {"symbol": "AAPL", "timeframe": "1D"})

    assert key1 == key2


def test_cache_key_generation_ignores_dict_order(fake_clock):
    """Arg dict key order must not affect the generated cache key."""
    key1 = generate_cache_key("quote", {"symbol": "AAPL", "timeframe": "1D"})
    key2 = generate_cache_key("quote", {"timeframe": "1D", "symbol": "AAPL"})

    assert key1 == key2


def test_cache_key_generation_differs_for_different_args(fake_clock):
    """Different args for the same function produce a different key."""
    key1 = generate_cache_key("quote", {"symbol": "AAPL"})
    key2 = generate_cache_key("quote", {"symbol": "TSLA"})

    assert key1 != key2


# --- Overwrite semantics: cache_set on an existing key replaces it, no duplicates ---

def test_cache_set_overwrites_existing_key_without_duplication(cache_path, fake_clock):
    """Setting the same key twice results in exactly one line for that key."""
    cache_set("quote:AAPL", {"price": 1}, ttl_seconds=300)
    cache_set("quote:AAPL", {"price": 2}, ttl_seconds=300)

    lines = _read_lines(cache_path)

    assert len(lines) == 1
    assert lines[0]["response"] == {"price": 2}
