"""
Task 5A-6: Circuit Breaker Pattern

Tests for tv_cdp_health.py CircuitBreaker class.
Verifies state transitions (healthy -> unhealthy -> fallback), cached
fallback responses, success-driven recovery bookkeeping, manual reset,
and state-transition logging. Single-threaded only per the brief
("test single-threaded first") — no threading.Lock coverage here.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from tv_cdp_health import CircuitBreaker


# --- Test 1: Starts healthy ---

def test_circuit_breaker_starts_healthy():
    """A freshly constructed breaker has state='healthy' and zeroed counters."""
    breaker = CircuitBreaker()

    assert breaker.state == "healthy"
    assert breaker.failure_count == 0
    assert breaker.success_count == 0
    assert breaker.last_response is None


# --- Test 2: Increments failure count, re-raises, moves to unhealthy ---

def test_circuit_breaker_increments_failure_count():
    """
    A single failed call increments failure_count to 1, re-raises the
    original exception to the caller, and (since 1 < threshold of 3)
    leaves the breaker in 'unhealthy' rather than 'fallback'.
    """
    breaker = CircuitBreaker()
    mock_fn = Mock(side_effect=Exception("boom"))

    with pytest.raises(Exception, match="boom"):
        breaker.call(mock_fn)

    assert breaker.failure_count == 1
    assert breaker.state == "unhealthy"
    mock_fn.assert_called_once()


# --- Test 3: Switches to fallback after threshold failures ---

def test_circuit_breaker_switches_to_fallback_after_threshold():
    """Three consecutive failures (default threshold=3) flip state to 'fallback'."""
    breaker = CircuitBreaker(failure_threshold=3)
    mock_fn = Mock(side_effect=Exception("boom"))

    for _ in range(3):
        with pytest.raises(Exception):
            breaker.call(mock_fn)

    assert breaker.state == "fallback"
    assert breaker.failure_count == 3
    assert mock_fn.call_count == 3


# --- Test 4: Fallback state returns cached response without calling fn ---

def test_circuit_breaker_returns_cached_on_fallback():
    """
    Once in fallback state, call() must return last_response directly
    and must NOT invoke fn() at all (per brief: "no attempt to call fn").
    """
    breaker = CircuitBreaker()
    breaker.last_response = {"price": 123}
    breaker.state = "fallback"
    mock_fn = Mock(return_value="should not be reached")

    result = breaker.call(mock_fn)

    assert result == {"price": 123}
    mock_fn.assert_not_called()


# --- Test 5: Success bookkeeping resets failure counter, recovery_attempts wraps ---

def test_circuit_breaker_resets_on_success_calls():
    """
    After recovery_attempts (default 10) successful calls, success_count
    wraps back to 0 (the brief's "reset failure counter" recovery
    bookkeeping) and failure_count stays at 0 throughout since every
    single success already resets it per the brief's per-call contract.
    """
    breaker = CircuitBreaker(recovery_attempts=10)
    mock_fn = Mock(return_value="ok")

    for _ in range(10):
        result = breaker.call(mock_fn)
        assert result == "ok"

    assert breaker.success_count == 0
    assert breaker.failure_count == 0
    assert breaker.state == "healthy"
    assert mock_fn.call_count == 10


# --- Test 6: reset() manually restores healthy state ---

def test_circuit_breaker_reset_method():
    """reset() unconditionally restores state='healthy' and zeroes both counters."""
    breaker = CircuitBreaker()
    breaker.state = "fallback"
    breaker.failure_count = 5
    breaker.success_count = 3

    breaker.reset()

    assert breaker.state == "healthy"
    assert breaker.failure_count == 0
    assert breaker.success_count == 0


# --- Additional: a success resets failure_count and caches the response ---

def test_circuit_breaker_success_resets_failure_count_and_caches():
    """
    A successful call after some (non-threshold) failures resets
    failure_count to 0, returns to 'healthy', and stores the result as
    last_response for future fallback use.
    """
    breaker = CircuitBreaker()
    fail_fn = Mock(side_effect=Exception("boom"))
    ok_fn = Mock(return_value="fresh-data")

    for _ in range(2):
        with pytest.raises(Exception):
            breaker.call(fail_fn)
    assert breaker.state == "unhealthy"
    assert breaker.failure_count == 2

    result = breaker.call(ok_fn)

    assert result == "fresh-data"
    assert breaker.failure_count == 0
    assert breaker.state == "healthy"
    assert breaker.last_response == "fresh-data"


# --- Additional: fallback reads never mutate the cache (read-only) ---

def test_circuit_breaker_fallback_does_not_mutate_cache_or_counters():
    """
    Per brief's "No side effects on cache" constraint: repeated fallback
    reads must not change last_response, failure_count, success_count,
    or state.
    """
    breaker = CircuitBreaker()
    breaker.last_response = "cached-value"
    breaker.state = "fallback"
    breaker.failure_count = 3
    mock_fn = Mock(return_value="new-value")

    for _ in range(5):
        result = breaker.call(mock_fn)
        assert result == "cached-value"

    assert breaker.last_response == "cached-value"
    assert breaker.failure_count == 3
    assert breaker.success_count == 0
    assert breaker.state == "fallback"
    mock_fn.assert_not_called()


# --- Additional: args/kwargs are passed through to fn ---

def test_circuit_breaker_passes_args_and_kwargs_to_fn():
    """call() must forward positional and keyword args through to fn()."""
    breaker = CircuitBreaker()
    mock_fn = Mock(return_value="result")

    result = breaker.call(mock_fn, "sym", timeframe="1D", retries=2)

    assert result == "result"
    mock_fn.assert_called_once_with("sym", timeframe="1D", retries=2)


# --- Additional: state-transition logging per Global Constraints ---

def test_circuit_breaker_logs_fallback_transition(caplog):
    """
    Global Constraints requires logging state transitions, e.g.
    "Circuit breaker: switching to fallback".
    """
    breaker = CircuitBreaker(failure_threshold=3)
    mock_fn = Mock(side_effect=Exception("boom"))

    with caplog.at_level(logging.INFO):
        for _ in range(3):
            with pytest.raises(Exception):
                breaker.call(mock_fn)

    assert any(
        "Circuit breaker" in record.message and "fallback" in record.message
        for record in caplog.records
    )


# --- Additional: custom failure_threshold is honored ---

def test_circuit_breaker_custom_failure_threshold():
    """A breaker constructed with failure_threshold=2 enters fallback after 2 failures."""
    breaker = CircuitBreaker(failure_threshold=2)
    mock_fn = Mock(side_effect=Exception("boom"))

    with pytest.raises(Exception):
        breaker.call(mock_fn)
    assert breaker.state == "unhealthy"

    with pytest.raises(Exception):
        breaker.call(mock_fn)
    assert breaker.state == "fallback"
