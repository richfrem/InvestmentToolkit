"""
Task 5D-4: Local Caching

Tests for data_window_validator.py's cache_data_window() — a thin wrapper
around tv_cdp_health.py's already-built, already-tested generic
file-based TTL cache (cache_get()/cache_set(), Task 5A-7). See this
task's brief for why entries deliberately share the SAME physical cache
file (tv_cdp_responses_cache.jsonl) as other tv_call() response caching,
namespaced under a "data_window:" prefix rather than a separate
data_window_cache.jsonl file.

IMPORTANT: All tests monkeypatch the module-level TV_CDP_CACHE_PATH
constant (on the tv_cdp_health module) to a pytest tmp_path location —
the exact same fixture pattern as 5A-7's own test file,
test_cache_fallback_on_circuit_break.py. None of these tests may write
to the real investment_screener/backend/data/tv_cdp_responses_cache.jsonl
path.

IMPORTANT: TTL expiry is simulated by monkeypatching tv_cdp_health.time.time
(the module's imported `time` object), never by a real time.sleep() —
same technique as 5A-7's own tests.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import tv_cdp_health  # noqa: E402
from tv_cdp_health import cache_get  # noqa: E402
from data_window_validator import cache_data_window  # noqa: E402


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


# --- Test 1: cache_data_window stores and returns True ---

def test_cache_data_window_stores_and_returns_true(cache_path, fake_clock):
    """A successful cache_data_window() call reports True (read-back verified)."""
    result = cache_data_window("NVDA:1D", {"open": 217.04, "close": 216.10})

    assert result is True


# --- Test 2: round-trips via the namespaced key through cache_get ---

def test_cache_data_window_round_trips_via_cache_get(cache_path, fake_clock):
    """The exact same data dict is retrievable via the namespaced key."""
    data = {"open": 217.04, "high": 222.75, "low": 215.28, "close": 216.10}
    cache_data_window("NVDA:1D", data)

    result = cache_get("data_window:NVDA:1D")

    assert result == data


# --- Test 3: respects TTL expiry ---

def test_cache_data_window_respects_ttl_expiry(cache_path, fake_clock):
    """An entry cached with ttl=60 is gone (via cache_get) once 60s+ elapse."""
    cache_data_window("NVDA:1D", {"open": 217.04}, ttl=60)

    fake_clock.now += 61

    result = cache_get("data_window:NVDA:1D")

    assert result is None


# --- Test 4: default TTL really is 300 seconds ---

def test_cache_data_window_uses_default_ttl_of_300(cache_path, fake_clock):
    """Without an explicit ttl, the entry survives 299s but not 301s."""
    cache_data_window("NVDA:1D", {"open": 217.04})

    fake_clock.now += 299
    assert cache_get("data_window:NVDA:1D") == {"open": 217.04}

    fake_clock.now += 2  # total elapsed: 301s
    assert cache_get("data_window:NVDA:1D") is None


# --- Test 5: different keys do not collide ---

def test_cache_data_window_different_keys_do_not_collide(cache_path, fake_clock):
    """Two distinct keys are independently retrievable and distinct."""
    cache_data_window("NVDA:1D", {"open": 217.04})
    cache_data_window("AAPL:1D", {"open": 195.50})

    assert cache_get("data_window:NVDA:1D") == {"open": 217.04}
    assert cache_get("data_window:AAPL:1D") == {"open": 195.50}


# --- Test 6: namespacing prevents collision with a raw tv_call() cache entry ---

def test_cache_data_window_key_namespacing_prevents_collision_with_raw_tv_call_cache(
    cache_path, fake_clock
):
    """A pre-existing raw tv_call() cache entry sharing the literal key
    string does not collide with cache_data_window()'s namespaced entry —
    both remain independently retrievable under their own real keys."""
    tv_cdp_health.cache_set("NVDA:1D", {"unrelated": "raw tv_call entry"})

    cache_data_window("NVDA:1D", {"open": 217.04})

    assert cache_get("NVDA:1D") == {"unrelated": "raw tv_call entry"}
    assert cache_get("data_window:NVDA:1D") == {"open": 217.04}


# --- Test 7: honest False when write verification fails ---

def test_cache_data_window_returns_false_when_write_verification_fails(
    cache_path, fake_clock, monkeypatch
):
    """If the read-back verification (cache_get) can't find the entry —
    e.g. a write that silently failed inside cache_set() — cache_data_window()
    reports False rather than a hollow, unconditional True."""
    import data_window_validator

    monkeypatch.setattr(data_window_validator, "cache_get", lambda key: None)

    result = cache_data_window("NVDA:1D", {"open": 217.04})

    assert result is False
