"""
Task 5A-3: Retry with Exponential Backoff

Tests for tv_cdp_health.py retry_with_backoff() function.
Verifies exponential delay sequencing, success/failure paths, and that
all tests run with time.sleep() mocked (no real wall-clock delay).
"""

import sys
from pathlib import Path
from unittest.mock import patch, Mock, call

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from tv_cdp_health import retry_with_backoff


# --- Test 1: Succeeds on first attempt, no retries ---

def test_retry_succeeds_on_first_attempt():
    """
    When fn() succeeds immediately, retry_with_backoff() should return
    its result without sleeping or retrying.
    """
    mock_fn = Mock(return_value="success")

    with patch("time.sleep") as mock_sleep:
        result = retry_with_backoff(mock_fn)

        assert result == "success"
        mock_fn.assert_called_once()
        mock_sleep.assert_not_called()


# --- Test 2: Exponential backoff delays between failures ---

def test_retry_exponential_backoff_delays():
    """
    When fn() fails twice then succeeds, retry_with_backoff() should
    sleep(1), then sleep(2), then return the successful result.
    """
    mock_fn = Mock(side_effect=[Exception("boom1"), Exception("boom2"), "success"])

    with patch("time.sleep") as mock_sleep:
        result = retry_with_backoff(mock_fn)

        assert result == "success"
        assert mock_fn.call_count == 3
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])
        assert mock_sleep.call_count == 2


# --- Test 3: Raises after max_attempts failures ---

def test_retry_raises_after_max_attempts():
    """
    When fn() always fails, retry_with_backoff() should raise the last
    exception after max_attempts tries, without retrying further.
    """
    mock_fn = Mock(side_effect=Exception("always fails"))

    with patch("time.sleep"):
        with pytest.raises(Exception) as exc_info:
            retry_with_backoff(mock_fn, max_attempts=3)

        assert "always fails" in str(exc_info.value)
        assert mock_fn.call_count == 3


# --- Test 4: Custom max_attempts ---

def test_retry_custom_max_attempts():
    """
    With max_attempts=5 and fn() always failing, retry_with_backoff()
    should attempt exactly 5 calls before raising.
    """
    mock_fn = Mock(side_effect=Exception("nope"))

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(Exception):
            retry_with_backoff(mock_fn, max_attempts=5)

        assert mock_fn.call_count == 5
        # 4 sleeps between 5 attempts
        assert mock_sleep.call_count == 4


# --- Test 5: Custom backoff factor ---

def test_retry_custom_backoff_factor():
    """
    With backoff_factor=3, delays should be 1s, 3s, 9s for successive
    retries.
    """
    mock_fn = Mock(side_effect=[Exception("a"), Exception("b"), Exception("c"), "success"])

    with patch("time.sleep") as mock_sleep:
        result = retry_with_backoff(mock_fn, max_attempts=4, backoff_factor=3.0)

        assert result == "success"
        mock_sleep.assert_has_calls([call(1.0), call(3.0), call(9.0)])
        assert mock_sleep.call_count == 3


# --- Test 6: Preserves exception message from fn() ---

def test_retry_preserves_exception_message():
    """
    The exception raised after exhausting max_attempts should preserve
    the original exception message/type from fn()'s last failure.
    """
    mock_fn = Mock(side_effect=ValueError("specific failure detail"))

    with patch("time.sleep"):
        with pytest.raises(ValueError) as exc_info:
            retry_with_backoff(mock_fn, max_attempts=2)

        assert str(exc_info.value) == "specific failure detail"


# --- Additional: default parameters sanity check ---

def test_retry_default_parameters():
    """
    Default max_attempts=3, backoff_factor=2.0, initial_delay_seconds=1.0
    should produce sleeps of 1s then 2s before raising on 3rd failure.
    """
    mock_fn = Mock(side_effect=Exception("fail"))

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(Exception):
            retry_with_backoff(mock_fn)

        assert mock_fn.call_count == 3
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])


# --- Additional: no side effects — fn args/kwargs are not mutated, no globals touched ---

def test_retry_is_pure_no_side_effects_on_repeated_calls():
    """
    Calling retry_with_backoff() twice with independent mocks should not
    leak state between calls (pure helper, no module-level mutation).
    """
    mock_fn_1 = Mock(return_value="first")
    mock_fn_2 = Mock(return_value="second")

    with patch("time.sleep"):
        result_1 = retry_with_backoff(mock_fn_1)
        result_2 = retry_with_backoff(mock_fn_2)

        assert result_1 == "first"
        assert result_2 == "second"
        mock_fn_1.assert_called_once()
        mock_fn_2.assert_called_once()


# --- Additional: invalid max_attempts guarded with a clear ValueError ---

def test_retry_raises_value_error_for_invalid_max_attempts():
    """
    max_attempts <= 0 must raise ValueError immediately (mentioning
    max_attempts in the message) rather than letting the loop skip
    entirely and later crash with `raise None`
    (TypeError: exceptions must derive from BaseException).
    """
    mock_fn = Mock(return_value="unused")

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(ValueError, match="max_attempts"):
            retry_with_backoff(mock_fn, max_attempts=0)

        with pytest.raises(ValueError, match="max_attempts"):
            retry_with_backoff(mock_fn, max_attempts=-1)

        mock_fn.assert_not_called()
        mock_sleep.assert_not_called()
