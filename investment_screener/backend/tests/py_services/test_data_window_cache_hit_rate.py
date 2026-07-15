"""
Task 5D-5: Cache Hit Logic

Tests for data_window_validator.py's get_cached_or_fetch() — a generic
cache-aside function that checks the Task 5D-4 cache first (via
tv_cdp_health.py's cache_get(), Task 5A-7) and only calls a caller-supplied
fetch_fn() on a genuine miss, caching a non-None result via 5D-4's own
cache_data_window() so entries are visible to both functions
interchangeably.

IMPORTANT: All tests monkeypatch the module-level TV_CDP_CACHE_PATH
constant (on the tv_cdp_health module) to a pytest tmp_path location —
the exact same fixture pattern as 5D-4's own test file,
test_data_window_cache_ttl_expiry.py. None of these tests may write to the
real investment_screener/backend/data/tv_cdp_responses_cache.jsonl path.

IMPORTANT: TTL expiry is simulated by monkeypatching tv_cdp_health.time.time
(the module's imported `time` object), never by a real time.sleep() — same
technique as 5A-7's/5D-4's own tests.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import tv_cdp_health  # noqa: E402
from tv_cdp_health import cache_get  # noqa: E402
from data_window_validator import cache_data_window, get_cached_or_fetch  # noqa: E402


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


def _never_call(*args, **kwargs):
    """A fetch_fn stand-in that fails the test if it's ever invoked —
    proves get_cached_or_fetch() didn't call fetch_fn on a cache hit."""
    raise AssertionError(f"fetch_fn must not be invoked, but was called with args={args}, kwargs={kwargs}")


# --- Test 1: returns cached value on a hit, never calls fetch_fn ---

def test_get_cached_or_fetch_returns_cached_value_on_hit(cache_path, fake_clock):
    """A pre-populated cache entry is returned as-is; fetch_fn is never called."""
    data = {"open": 217.04, "close": 216.10}
    cache_data_window("NVDA:1D", data)

    result = get_cached_or_fetch("NVDA:1D", _never_call)

    assert result == data


# --- Test 2: calls fetch_fn on a miss ---

def test_get_cached_or_fetch_calls_fetch_fn_on_miss(cache_path, fake_clock):
    """An empty cache results in exactly one fetch_fn() call, whose return
    value is returned as-is."""
    call_count = {"n": 0}
    fresh_data = {"open": 195.50, "close": 196.10}

    def fetch_fn():
        call_count["n"] += 1
        return fresh_data

    result = get_cached_or_fetch("AAPL:1D", fetch_fn)

    assert result == fresh_data
    assert call_count["n"] == 1


# --- Test 3: caches the fresh result on a miss ---

def test_get_cached_or_fetch_caches_fresh_result_on_miss(cache_path, fake_clock):
    """After a miss that returns real data, the fresh result is actually
    persisted for a subsequent call (direct cache_get()) to find."""
    fresh_data = {"open": 100.0, "close": 101.0}

    get_cached_or_fetch("MSFT:1D", lambda: fresh_data)

    assert cache_get("data_window:MSFT:1D") == fresh_data


# --- Test 4: a None fetch result is not cached ---

def test_get_cached_or_fetch_does_not_cache_none_result(cache_path, fake_clock):
    """fetch_fn returning None (matching extract_data_window()'s "gave up
    after retries" outcome) is returned as-is and NOT written to the
    cache — caching it would poison the cache for the full TTL window."""
    result = get_cached_or_fetch("TSLA:1D", lambda: None)

    assert result is None
    assert cache_get("data_window:TSLA:1D") is None


# --- Test 5: respects a custom ttl on a miss ---

def test_get_cached_or_fetch_respects_custom_ttl_on_miss(cache_path, fake_clock):
    """A fresh entry cached with ttl=60 is gone (via cache_get) once 60s+
    elapse — not the default 300."""
    fresh_data = {"open": 50.0}

    get_cached_or_fetch("SPY:1D", lambda: fresh_data, ttl=60)

    fake_clock.now += 61

    assert cache_get("data_window:SPY:1D") is None


# --- Test 6: an expired entry is treated as a miss ---

def test_get_cached_or_fetch_treats_expired_entry_as_a_miss(cache_path, fake_clock):
    """An entry cached with a short TTL that has since expired does NOT
    count as a hit — fetch_fn IS called and its fresh result returned."""
    cache_data_window("QQQ:1D", {"open": 10.0}, ttl=60)
    fake_clock.now += 61

    call_count = {"n": 0}
    fresh_data = {"open": 11.0}

    def fetch_fn():
        call_count["n"] += 1
        return fresh_data

    result = get_cached_or_fetch("QQQ:1D", fetch_fn)

    assert result == fresh_data
    assert call_count["n"] == 1


# --- Test 7: interoperates with cache_data_window() in both directions ---

def test_get_cached_or_fetch_interoperates_with_cache_data_window(cache_path, fake_clock):
    """An entry written via cache_data_window() (5D-4) directly is found
    as a hit by get_cached_or_fetch() (this function) — confirms the
    shared "data_window:" namespacing convention genuinely works both
    directions, not just within one function's own test suite."""
    data = {"open": 300.0, "close": 301.0}
    cache_data_window("GOOG:1D", data)

    result = get_cached_or_fetch("GOOG:1D", _never_call)

    assert result == data


# --- Test 8: fetch_fn's own exception propagates uncaught ---

def test_get_cached_or_fetch_propagates_fetch_fn_exception(cache_path, fake_clock):
    """fetch_fn raising is NOT swallowed into None or any other value —
    it propagates uncaught to the caller."""
    def fetch_fn():
        raise ValueError("fetch failed")

    with pytest.raises(ValueError, match="fetch failed"):
        get_cached_or_fetch("IBM:1D", fetch_fn)
