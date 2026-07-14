"""
Task 5D-6: Lag-Tolerant Extraction

Tests for data_window_validator.extract_with_lag_logging() — a thin
observability wrapper around extract_data_window() (Task 5D-1, already
shipped) that times the full call and logs a single "Data window lagged
by Xs" warning if it took meaningfully longer than a clean single
attempt would.

Per this task's brief: extract_data_window() already implements
retry-with-backoff and last-known-good semantics. This wrapper does NOT
reimplement any of that — it calls extract_data_window() exactly once
and passes its return value through unmodified. `extract_data_window`
is monkeypatched at the data_window_validator module's own reference
(not tv_call) so these tests control both the return value and (via a
mocked time.monotonic) the simulated elapsed duration without needing
real retries or real tv_call mocking.
"""

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import data_window_validator  # noqa: E402
from data_window_validator import extract_with_lag_logging  # noqa: E402


_SAMPLE_CANDLE = {
    "open": 217.04,
    "high": 222.75,
    "low": 215.28,
    "close": 216.10,
    "volume": 1_640_000,
    "timestamp": "2026-07-14T00:00:00+00:00",
}


def _make_fake_monotonic(values):
    """Return a zero-arg callable that yields successive values from
    `values` on each call, matching time.monotonic()'s real signature."""
    calls = {"index": 0}

    def fake_monotonic():
        idx = calls["index"]
        calls["index"] += 1
        if idx < len(values):
            return values[idx]
        return values[-1]

    return fake_monotonic


# --- Test 1: warning logged when the call is slow ---

def test_extract_with_lag_logging_logs_warning_when_slow(monkeypatch, caplog):
    monkeypatch.setattr(
        data_window_validator.time,
        "monotonic",
        _make_fake_monotonic([0.0, data_window_validator._LAG_WARNING_THRESHOLD_SECONDS]),
    )
    monkeypatch.setattr(
        data_window_validator, "extract_data_window", lambda ticker, timeframe: dict(_SAMPLE_CANDLE)
    )

    with caplog.at_level(logging.WARNING):
        result = extract_with_lag_logging("NVDA")

    assert result == _SAMPLE_CANDLE
    assert any(
        "Data window lagged" in record.message and "NVDA" in record.message
        for record in caplog.records
    )


# --- Test 2: no warning logged when the call is fast ---

def test_extract_with_lag_logging_does_not_log_when_fast(monkeypatch, caplog):
    monkeypatch.setattr(data_window_validator.time, "monotonic", _make_fake_monotonic([0.0, 0.1]))
    monkeypatch.setattr(
        data_window_validator, "extract_data_window", lambda ticker, timeframe: dict(_SAMPLE_CANDLE)
    )

    with caplog.at_level(logging.WARNING):
        result = extract_with_lag_logging("NVDA")

    assert result == _SAMPLE_CANDLE
    assert not any("Data window lagged" in record.message for record in caplog.records)


# --- Test 3: return value is exactly extract_data_window()'s result, unchanged ---

def test_extract_with_lag_logging_returns_extract_data_window_result_unchanged(monkeypatch):
    monkeypatch.setattr(data_window_validator.time, "monotonic", _make_fake_monotonic([0.0, 0.1]))
    candle = dict(_SAMPLE_CANDLE)
    monkeypatch.setattr(data_window_validator, "extract_data_window", lambda ticker, timeframe: candle)

    result = extract_with_lag_logging("NVDA")

    assert result == candle


# --- Test 4: passes through a None result (extract_data_window()'s own
# "gave up after retries" contract) unchanged, and lag logging still
# runs correctly based on elapsed time regardless ---

def test_extract_with_lag_logging_passes_through_none_result(monkeypatch, caplog):
    monkeypatch.setattr(
        data_window_validator.time,
        "monotonic",
        _make_fake_monotonic([0.0, data_window_validator._LAG_WARNING_THRESHOLD_SECONDS + 1]),
    )
    monkeypatch.setattr(data_window_validator, "extract_data_window", lambda ticker, timeframe: None)

    with caplog.at_level(logging.WARNING):
        result = extract_with_lag_logging("NVDA")

    assert result is None
    assert any("Data window lagged" in record.message for record in caplog.records)


# --- Test 5: extract_data_window() is called with exactly (ticker, timeframe) ---

def test_extract_with_lag_logging_calls_extract_data_window_with_correct_args(monkeypatch):
    monkeypatch.setattr(data_window_validator.time, "monotonic", _make_fake_monotonic([0.0, 0.1]))
    calls = []

    def fake_extract_data_window(ticker, timeframe):
        calls.append((ticker, timeframe))
        return dict(_SAMPLE_CANDLE)

    monkeypatch.setattr(data_window_validator, "extract_data_window", fake_extract_data_window)

    extract_with_lag_logging("NVDA", timeframe="60")

    assert calls == [("NVDA", "60")]


# --- Test 6: logged message's numeric content matches the simulated elapsed time ---

def test_extract_with_lag_logging_log_message_includes_elapsed_seconds(monkeypatch, caplog):
    monkeypatch.setattr(data_window_validator.time, "monotonic", _make_fake_monotonic([0.0, 3.0]))
    monkeypatch.setattr(
        data_window_validator, "extract_data_window", lambda ticker, timeframe: dict(_SAMPLE_CANDLE)
    )

    with caplog.at_level(logging.WARNING):
        extract_with_lag_logging("NVDA")

    assert any("3.0s" in record.message for record in caplog.records)
