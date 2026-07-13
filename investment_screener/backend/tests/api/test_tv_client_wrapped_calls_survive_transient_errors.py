"""
Task 5A-8: Integration into tv_client.py

Tests for the resilience-wrapped tv_call() in
plugins/tradingview/scripts/tv_client.py — the final integration point
that composes retry (5A-3), circuit breaker (5A-6), structural
validation (5A-4 scope-boundary, see below), and disk cache fallback
(5A-7) around the single-attempt TV CLI call, with every failure logged
to tv_cdp_errors.jsonl (5A-5).

Design notes these tests assert on:

  - Success path is a raw passthrough: on a fresh, valid, successful
    call, tv_call() returns the exact dict the CLI produced — unchanged
    from pre-5A-8 behavior. This is what keeps all 19 real positional
    call sites (tv_health_check.py, tv_batch_quotes.py, etc.) working
    without modification.
  - Failure path never raises. It returns
    {"error": str, "data": None | dict, "cached": bool, "timestamp": str}.
  - `_tv_call_once()` is the extracted single-attempt seam (the exact
    original tv_call() body) — tests monkeypatch this instead of
    shelling out to a real `node cli.js` subprocess.
  - The module-level circuit breaker (`tv_client._circuit_breaker`) is a
    process-lifetime singleton, so every test resets it via the
    `reset_breaker` autouse fixture to avoid cross-test state leakage.
  - Validation here is a deliberate scope boundary: no per-command
    pydantic schema exists at this generic (command: str, *args) layer,
    so `enable_validation=True` only checks that the parsed response is
    a non-empty dict, not None/list/malformed. Real schema-based
    validate_tv_response() checks remain available to higher-level
    callers that know their expected shape.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
TV_SCRIPTS_DIR = REPO_ROOT / "plugins/tradingview/scripts"
HEALTH_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(TV_SCRIPTS_DIR))
sys.path.insert(0, str(HEALTH_DIR))

import tv_client  # noqa: E402
import tv_cdp_health  # noqa: E402


@pytest.fixture(autouse=True)
def reset_breaker():
    """Reset the module-level circuit breaker singleton before every test."""
    tv_client._circuit_breaker.reset()
    yield
    tv_client._circuit_breaker.reset()


@pytest.fixture
def isolated_jsonl_paths(tmp_path, monkeypatch):
    """Redirect the errors JSONL and cache JSONL to tmp_path for this test."""
    errors_path = tmp_path / "tv_cdp_errors.jsonl"
    cache_path = tmp_path / "tv_cdp_responses_cache.jsonl"
    monkeypatch.setattr(tv_cdp_health, "TV_CDP_ERRORS_PATH", errors_path)
    monkeypatch.setattr(tv_cdp_health, "TV_CDP_CACHE_PATH", cache_path)
    return {"errors": errors_path, "cache": cache_path}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- Test 1: retry succeeds on second attempt ---

def test_tv_call_with_retry_succeeds_on_second_attempt(isolated_jsonl_paths, monkeypatch):
    """A transient failure on attempt 1 is retried and succeeds on attempt 2."""
    calls = {"count": 0}

    def flaky(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("transient CDP hiccup")
        return {"success": True, "value": 42}

    monkeypatch.setattr(tv_client, "_tv_call_once", flaky)
    monkeypatch.setattr(tv_client.time, "sleep", lambda *_: None)

    result = tv_client.tv_call("chart", "read")

    assert result == {"success": True, "value": 42}
    assert calls["count"] == 2


# --- Test 2: circuit breaker falls back to cached response on repeated failure ---

def test_tv_call_with_circuit_breaker_falls_back_on_repeated_failure(
    isolated_jsonl_paths, monkeypatch
):
    """
    After failure_threshold consecutive failures, the breaker opens and the
    next call is served from the last-known-good disk cache instead of
    hitting the (still-failing) TV CLI again.
    """
    monkeypatch.setattr(tv_client.time, "sleep", lambda *_: None)

    # Prime the disk cache with a last-known-good response for this exact
    # (command, args) pair, simulating an earlier successful call.
    cache_key = tv_client._make_cache_key(("watchlist", "get"))
    tv_cdp_health.cache_set(cache_key, {"success": True, "items": ["AAPL"]})

    def always_fails(*args, **kwargs):
        raise RuntimeError("TV CDP unreachable")

    monkeypatch.setattr(tv_client, "_tv_call_once", always_fails)

    # Drive the breaker to "fallback" state: failure_threshold=3 consecutive
    # failures, each call already exhausts enable_retry's max_attempts.
    for _ in range(3):
        tv_client.tv_call("watchlist", "get", enable_retry=False)

    assert tv_client._circuit_breaker.state == "fallback"

    result = tv_client.tv_call("watchlist", "get", enable_retry=False)

    assert result["cached"] is True
    assert result["data"] == {"success": True, "items": ["AAPL"]}
    assert "error" in result and isinstance(result["error"], str)


# --- Test 3: validation rejects a malformed (non-dict) response ---

def test_tv_call_with_validation_rejects_malformed_response(isolated_jsonl_paths, monkeypatch):
    """
    A structurally malformed response (not a non-empty dict) fails the
    generic structural check and tv_call() returns the error-dict contract
    instead of the malformed payload.
    """
    monkeypatch.setattr(tv_client, "_tv_call_once", lambda *a, **k: None)

    result = tv_client.tv_call("chart", "read", enable_retry=False, enable_circuit_breaker=False)

    assert result["error"] is not None
    assert result["data"] is None
    assert "timestamp" in result


# --- Test 4: every failure is logged to tv_cdp_errors.jsonl ---

def test_tv_call_logs_error_to_jsonl_on_failure(isolated_jsonl_paths, monkeypatch):
    """A failed call appends a record to tv_cdp_errors.jsonl (non-blocking)."""
    monkeypatch.setattr(tv_client.time, "sleep", lambda *_: None)

    def always_fails(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tv_client, "_tv_call_once", always_fails)

    tv_client.tv_call("chart", "read", enable_retry=False, enable_circuit_breaker=False)

    records = _read_jsonl(isolated_jsonl_paths["errors"])
    assert len(records) >= 1
    assert "boom" in records[-1]["error"]


# --- Test 5: backward compatible without new params ---

def test_tv_call_backward_compatible_without_new_params(isolated_jsonl_paths, monkeypatch):
    """
    Calling tv_call(cmd, symbol) exactly as the 19 real call sites do —
    positional args only, no resilience kwargs — still returns the raw
    successful response unchanged.
    """
    monkeypatch.setattr(
        tv_client, "_tv_call_once", lambda *a, **k: {"success": True, "symbol": "AAPL"}
    )

    result = tv_client.tv_call("chart", "symbol", "AAPL")

    assert result == {"success": True, "symbol": "AAPL"}


# --- Test 6: complete failure across all layers never raises ---

def test_tv_call_returns_dict_never_raises(isolated_jsonl_paths, monkeypatch):
    """
    When retry, circuit breaker, and cache fallback all fail to produce a
    usable response, tv_call() returns {error, data: None, ...} — it must
    never propagate an exception to the caller.
    """
    monkeypatch.setattr(tv_client.time, "sleep", lambda *_: None)

    def always_fails(*args, **kwargs):
        raise RuntimeError("total outage")

    monkeypatch.setattr(tv_client, "_tv_call_once", always_fails)

    try:
        result = tv_client.tv_call("chart", "read")
    except Exception as e:  # pragma: no cover - the assertion below is the real check
        pytest.fail(f"tv_call() raised {e!r} instead of returning an error dict")

    assert isinstance(result, dict)
    assert isinstance(result["error"], str)
    assert result["data"] is None


# --- Additional: cache_fallback disabled means no disk cache read/write ---

def test_tv_call_with_cache_fallback_disabled_returns_plain_error(isolated_jsonl_paths, monkeypatch):
    """enable_cache_fallback=False must skip cache reads even if a hit would exist."""
    monkeypatch.setattr(tv_client.time, "sleep", lambda *_: None)

    cache_key = tv_client._make_cache_key(("chart", "read"))
    tv_cdp_health.cache_set(cache_key, {"stale": True})

    def always_fails(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(tv_client, "_tv_call_once", always_fails)

    result = tv_client.tv_call(
        "chart", "read", enable_retry=False, enable_circuit_breaker=False, enable_cache_fallback=False
    )

    assert result["cached"] is False
    assert result["data"] is None


# --- Additional: successful calls write through to the disk cache ---

def test_tv_call_success_writes_through_to_cache(isolated_jsonl_paths, monkeypatch):
    """A fresh successful call populates the disk cache for future fallback."""
    monkeypatch.setattr(
        tv_client, "_tv_call_once", lambda *a, **k: {"success": True, "value": 1}
    )

    tv_client.tv_call("chart", "read")

    cache_key = tv_client._make_cache_key(("chart", "read"))
    assert tv_cdp_health.cache_get(cache_key) == {"success": True, "value": 1}


# --- Additional: missing/broken resilience dependency degrades to pre-5A-8 behavior ---

def test_tv_call_falls_back_to_tv_call_once_when_resilience_import_failed(monkeypatch):
    """
    When `_RESILIENCE_IMPORT_ERROR` is set (simulating a missing/broken
    resilience dependency, e.g. pydantic unavailable at import time — see
    tv_client.py's own try/except around the tv_cdp_health import), tv_call()
    must route straight to `_tv_call_once()` — bypassing retry, circuit
    breaker, validation, and disk cache entirely — rather than crashing with
    a NameError on any of the resilience names that are unbound in that
    scenario (retry_with_backoff, CircuitBreaker, log_tv_error, cache_get,
    cache_set, generate_cache_key).

    This also confirms `_tv_call_once()`'s pre-5A-8 contract (it MAY raise)
    is preserved on this fallback path: tv_call() must let that exception
    propagate unchanged, not swallow it into an error dict.
    """
    monkeypatch.setattr(tv_client, "_RESILIENCE_IMPORT_ERROR", "pydantic unavailable")

    calls = {"count": 0}

    def fake_once(*args, **kwargs):
        calls["count"] += 1
        return {"success": True, "value": "bypassed-resilience"}

    monkeypatch.setattr(tv_client, "_tv_call_once", fake_once)

    result = tv_client.tv_call("chart", "read")

    assert result == {"success": True, "value": "bypassed-resilience"}
    assert calls["count"] == 1

    # And confirm the raise-based pre-5A-8 contract survives on this path.
    def fake_once_raises(*args, **kwargs):
        raise RuntimeError("CDP unreachable")

    monkeypatch.setattr(tv_client, "_tv_call_once", fake_once_raises)

    with pytest.raises(RuntimeError, match="CDP unreachable"):
        tv_client.tv_call("chart", "read")
