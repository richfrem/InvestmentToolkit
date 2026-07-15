"""
Task 5D-2: OHLCV Validation

Tests for data_window_validator.validate_ohlcv(), a pure, offline
validation function operating on a candle dict matching
extract_data_window()'s (Task 5D-1) real output shape. Does NOT call
extract_data_window() or any tv_call()-based function — no TV CDP
mocking is needed here, only plain dict fixtures.

Per this task's brief, the relational check set is deliberately
incomplete (O<=H, H>=L, L<=C only — no L<=O/C<=H), and "spread" is
interpreted as intraday range as a percentage of low (no bid/ask data
is available in the real candle shape).
"""

import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from data_window_validator import validate_ohlcv  # noqa: E402


def _valid_candle(**overrides):
    """A real, internally-consistent candle (matching 5D-1's real
    live-sampled shape).

    Note: the brief's own illustrative ("e.g.") sample values
    (open=217.04, high=222.75, low=215.28, close=216.10) have an
    intraday spread of ~3.47% ((222.75-215.28)/215.28*100), which
    exceeds the very 2% spread threshold this task also mandates —
    those exact literal numbers cannot simultaneously satisfy "valid,
    errors=[]" AND the spread check. Since the brief marks them "e.g."
    (illustrative of shape/style, not a literal fixed requirement),
    `high` is tightened here (218.50 vs. the sample's 222.75) so the
    fixture is genuinely internally-consistent under all of this
    module's checks while keeping the same real-sampled character.
    """
    base = {
        "open": 217.04,
        "high": 218.50,
        "low": 215.28,
        "close": 216.10,
        "volume": 1_640_000,
        "timestamp": "2026-07-14T00:00:00+00:00",
    }
    base.update(overrides)
    return base


# --- Test 1: accepts a valid, internally-consistent candle ---

def test_validate_ohlcv_accepts_valid_candle():
    result = validate_ohlcv(_valid_candle())

    assert result == {"valid": True, "errors": []}


# --- Test 2: rejects open > high ---

def test_validate_ohlcv_rejects_open_greater_than_high():
    result = validate_ohlcv(_valid_candle(open=230, high=222.75))

    assert result["valid"] is False
    assert any("open" in e.lower() and "high" in e.lower() for e in result["errors"])


# --- Test 3: rejects high < low ---

def test_validate_ohlcv_rejects_high_less_than_low():
    result = validate_ohlcv(_valid_candle(high=210, low=215.28))

    assert result["valid"] is False
    assert any("high" in e.lower() and "low" in e.lower() for e in result["errors"])


# --- Test 4: rejects low > close ---

def test_validate_ohlcv_rejects_low_greater_than_close():
    result = validate_ohlcv(_valid_candle(low=220, close=216.10))

    assert result["valid"] is False
    assert any("low" in e.lower() and "close" in e.lower() for e in result["errors"])


# --- Test 5: rejects zero or negative volume ---

@pytest.mark.parametrize("volume", [0, -100])
def test_validate_ohlcv_rejects_zero_or_negative_volume(volume):
    result = validate_ohlcv(_valid_candle(volume=volume))

    assert result["valid"] is False
    assert any("volume" in e.lower() for e in result["errors"])


# --- Test 6: accepts missing/None volume (soft check) ---

def test_validate_ohlcv_accepts_missing_volume():
    result = validate_ohlcv(_valid_candle(volume=None))

    assert result == {"valid": True, "errors": []}


# --- Test 7: rejects NaN or inf price fields, no exception ---

def test_validate_ohlcv_rejects_nan_or_inf_price_field():
    nan_result = validate_ohlcv(_valid_candle(close=float("nan")))
    inf_result = validate_ohlcv(_valid_candle(high=float("inf")))

    assert nan_result["valid"] is False
    assert nan_result["errors"]
    assert inf_result["valid"] is False
    assert inf_result["errors"]


# --- Test 8: rejects missing price field (None), no TypeError ---

def test_validate_ohlcv_rejects_missing_price_field():
    result = validate_ohlcv(_valid_candle(close=None))

    assert result["valid"] is False
    assert any("close" in e.lower() for e in result["errors"])


# --- Test 9: rejects wide spread (>= 2%) ---

def test_validate_ohlcv_rejects_wide_spread():
    result = validate_ohlcv(_valid_candle(open=100.5, high=103, low=100, close=101))

    assert result["valid"] is False
    assert any("spread" in e.lower() for e in result["errors"])


# --- Test 10: accepts narrow spread (< 2%) ---

def test_validate_ohlcv_accepts_narrow_spread():
    result = validate_ohlcv(_valid_candle(open=100.5, high=101, low=100, close=100.8))

    assert result == {"valid": True, "errors": []}


# --- Test 11: accumulates multiple errors (relational + volume) ---

def test_validate_ohlcv_accumulates_multiple_errors():
    result = validate_ohlcv(_valid_candle(open=230, high=222.75, volume=-100))

    assert result["valid"] is False
    assert len(result["errors"]) >= 2


# --- Test 12: never raises on non-dict input ---

@pytest.mark.parametrize("bad_input", [None, ["open", "high"], "not a dict"])
def test_validate_ohlcv_never_raises_on_non_dict_input(bad_input):
    result = validate_ohlcv(bad_input)

    assert result["valid"] is False
    assert isinstance(result["errors"], list)
    assert result["errors"]


# --- Test 13: rejects non-positive low without crashing (spread division guard) ---
#
# Bug found in task review: `_is_finite_number()` accepts 0.0 (and
# negative numbers) as "finite" — only None/bool/non-numeric/NaN/inf are
# rejected. A candle with low=0.0 therefore passes the price-field check
# and reaches `_validate_relations_and_spread()`'s
# `(high - low) / low * 100` division, raising ZeroDivisionError and
# violating this function's documented "never raises" contract.

@pytest.mark.parametrize("low", [0.0, -1.0])
def test_validate_ohlcv_rejects_zero_low_without_crashing(low):
    result = validate_ohlcv(_valid_candle(open=1.0, high=1.0, low=low, close=1.0))

    assert result["valid"] is False
    assert any("low" in e.lower() for e in result["errors"])


# --- Extra: _is_finite_number helper ---

@pytest.mark.parametrize("value,expected", [
    (1.0, True),
    (1, True),
    (0, True),
    (-5.5, True),
    (True, False),
    (False, False),
    (None, False),
    (float("nan"), False),
    (float("inf"), False),
    (float("-inf"), False),
    ("1.0", False),
])
def test_is_finite_number(value, expected):
    from data_window_validator import _is_finite_number

    assert _is_finite_number(value) is expected
