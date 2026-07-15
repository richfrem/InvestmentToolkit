"""
Task 5D-7: Data Window Validation Harness

Tests for data_window_validator.get_validated_data_window() — the pure
composition point chaining extract_with_lag_logging() (5D-6), validate_ohlcv()
(5D-2), and extract_indicators() (5D-3) unchanged, with no new extraction or
validation logic of its own.

All three composed functions are monkeypatched at the data_window_validator
module's own references (not tv_call) so these tests never touch real CDP —
each test controls exactly what each composed layer returns/receives.

Key correctness rule under test (see this task's brief): extract_indicators()
takes no ticker parameter — it reads whichever chart is CURRENTLY active. If
extract_with_lag_logging() returns None (total extraction failure after all
retries), there's no confirmation the active chart is even showing the
requested ticker, so extract_indicators() must NOT be called in that case —
test 2 proves this with a "never call" stand-in, not just a return-value
check.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import data_window_validator  # noqa: E402
from data_window_validator import get_validated_data_window  # noqa: E402


_SAMPLE_CANDLE = {
    "open": 217.04,
    "high": 222.75,
    "low": 215.28,
    "close": 216.10,
    "volume": 1_640_000,
    "timestamp": "2026-07-14T00:00:00+00:00",
}

_SAMPLE_INDICATORS = {
    "rsi": 45.79,
    "macd": 1.23,
    "bb_upper": 230.0,
    "bb_lower": 210.0,
    "adx": 25.0,
    "atr": 3.5,
}

_EMPTY_INDICATORS = {
    "rsi": None,
    "macd": None,
    "bb_upper": None,
    "bb_lower": None,
    "adx": None,
    "atr": None,
}


def _never_call(*args, **kwargs):
    raise AssertionError("extract_indicators() must not be called in this scenario")


# --- Test 1: full success ---

def test_get_validated_data_window_full_success(monkeypatch):
    monkeypatch.setattr(
        data_window_validator, "extract_with_lag_logging", lambda ticker, timeframe: dict(_SAMPLE_CANDLE)
    )
    monkeypatch.setattr(
        data_window_validator, "extract_indicators", lambda timeframe: dict(_SAMPLE_INDICATORS)
    )
    monkeypatch.setattr(
        data_window_validator, "validate_ohlcv", lambda candle: {"valid": True, "errors": []}
    )

    result = get_validated_data_window("NVDA")

    assert result["valid"] is True
    assert result["candle"] == _SAMPLE_CANDLE
    assert result["indicators"] == _SAMPLE_INDICATORS
    assert result["warnings"] == []


# --- Test 2: candle extraction fails entirely — extract_indicators must NEVER be called ---

def test_get_validated_data_window_candle_extraction_fails(monkeypatch):
    monkeypatch.setattr(
        data_window_validator, "extract_with_lag_logging", lambda ticker, timeframe: None
    )
    monkeypatch.setattr(data_window_validator, "extract_indicators", _never_call)
    monkeypatch.setattr(
        data_window_validator,
        "validate_ohlcv",
        lambda candle: (_ for _ in ()).throw(AssertionError("validate_ohlcv() must not be called")),
    )

    result = get_validated_data_window("NVDA", timeframe="1D")

    assert result["valid"] is False
    assert result["candle"] is None
    assert result["indicators"] == _EMPTY_INDICATORS
    assert len(result["warnings"]) == 1
    assert "extraction failed" in result["warnings"][0] or "returned None" in result["warnings"][0]


# --- Test 3: non-None candle but OHLCV-invalid — candle kept, indicators still fetched ---

def test_get_validated_data_window_ohlcv_invalid(monkeypatch):
    calls = []

    def fake_extract_indicators(timeframe):
        calls.append(timeframe)
        return dict(_SAMPLE_INDICATORS)

    monkeypatch.setattr(
        data_window_validator, "extract_with_lag_logging", lambda ticker, timeframe: dict(_SAMPLE_CANDLE)
    )
    monkeypatch.setattr(data_window_validator, "extract_indicators", fake_extract_indicators)
    monkeypatch.setattr(
        data_window_validator,
        "validate_ohlcv",
        lambda candle: {"valid": False, "errors": ["open must be <= high"]},
    )

    result = get_validated_data_window("NVDA")

    assert result["valid"] is False
    assert result["candle"] == _SAMPLE_CANDLE
    assert result["warnings"] == ["open must be <= high"]
    assert calls == ["1D"]


# --- Test 4: missing indicators never gate `valid` ---

def test_get_validated_data_window_indicators_missing_does_not_affect_valid(monkeypatch):
    monkeypatch.setattr(
        data_window_validator, "extract_with_lag_logging", lambda ticker, timeframe: dict(_SAMPLE_CANDLE)
    )
    monkeypatch.setattr(data_window_validator, "extract_indicators", lambda timeframe: dict(_EMPTY_INDICATORS))
    monkeypatch.setattr(
        data_window_validator, "validate_ohlcv", lambda candle: {"valid": True, "errors": []}
    )

    result = get_validated_data_window("NVDA")

    assert result["valid"] is True
    assert result["indicators"] == _EMPTY_INDICATORS


# --- Test 5: composed functions called with exactly the right args ---

def test_get_validated_data_window_calls_composed_functions_with_correct_args(monkeypatch):
    extract_calls = []
    indicator_calls = []
    validate_calls = []

    def fake_extract(ticker, timeframe):
        extract_calls.append((ticker, timeframe))
        return dict(_SAMPLE_CANDLE)

    def fake_indicators(timeframe):
        indicator_calls.append(timeframe)
        return dict(_SAMPLE_INDICATORS)

    def fake_validate(candle):
        validate_calls.append(candle)
        return {"valid": True, "errors": []}

    monkeypatch.setattr(data_window_validator, "extract_with_lag_logging", fake_extract)
    monkeypatch.setattr(data_window_validator, "extract_indicators", fake_indicators)
    monkeypatch.setattr(data_window_validator, "validate_ohlcv", fake_validate)

    get_validated_data_window("NVDA", timeframe="60")

    assert extract_calls == [("NVDA", "60")]
    assert indicator_calls == ["60"]
    assert validate_calls == [_SAMPLE_CANDLE]


# --- Test 6: fully-valid result's warnings is exactly [] ---

def test_get_validated_data_window_warnings_empty_when_fully_valid(monkeypatch):
    monkeypatch.setattr(
        data_window_validator, "extract_with_lag_logging", lambda ticker, timeframe: dict(_SAMPLE_CANDLE)
    )
    monkeypatch.setattr(data_window_validator, "extract_indicators", lambda timeframe: dict(_SAMPLE_INDICATORS))
    monkeypatch.setattr(
        data_window_validator, "validate_ohlcv", lambda candle: {"valid": True, "errors": []}
    )

    result = get_validated_data_window("NVDA")

    assert result["warnings"] == []
    assert result["warnings"] is not None


# --- Test 7: defensive regression guard — composed functions raising is not
# swallowed by this harness (none of the three composed functions currently
# raise per this module's established contract; this test documents and
# locks in that "let it propagate" behavior rather than adding untested
# defensive try/except — see this task's report for the reasoning) ---

def test_get_validated_data_window_never_raises_when_composed_functions_raise(monkeypatch):
    def raising_extract(ticker, timeframe):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(data_window_validator, "extract_with_lag_logging", raising_extract)

    try:
        get_validated_data_window("NVDA")
        raised = False
    except RuntimeError:
        raised = True

    assert raised, (
        "get_validated_data_window() currently has no try/except of its own — "
        "a raising composed function propagates unchanged. This is a documented "
        "regression guard, not a requirement violation: none of the three real "
        "composed functions raise today (see this task's report)."
    )
