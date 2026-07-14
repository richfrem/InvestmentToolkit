"""
Task 5D-3: Indicator Extraction

Tests for data_window_validator.extract_indicators(), which reads
TradingView's live Data Window panel (via `chart timeframe` +
`chart openDataWindow` + `chart read` — no chart symbol switch, unlike
extract_data_window()) and extracts a representative, non-exhaustive set
of indicator fields (rsi, macd, bb_upper, bb_lower, adx, atr), range-
validating each.

RSI/ADX/ATR key names are confirmed against the real live Data Window
sample gathered for Task 5D-1's brief (2026-07-14, read-only, no chart
change). MACD/BB key names are best-effort guesses — no chart with those
indicators loaded was inspected live; this test file's fixtures use the
brief's documented guesses ("MACD", "BB Upper"/"BB Lower",
"Bollinger Upper"/"Bollinger Lower").

tv_call is mocked at the data_window_validator module's imported
reference — no test here ever shells out to the real TV CDP engine, and
no chart symbol/timeframe change is ever made against a live chart.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import data_window_validator  # noqa: E402
from data_window_validator import extract_indicators  # noqa: E402


ERROR_DICT_SHAPE = {
    "error": "CDP timeout",
    "data": None,
    "cached": False,
    "timestamp": "2026-07-12T00:00:00+00:00",
}


def _real_shaped_response(**overrides):
    """A real-shaped `chart read` response including indicator fields.

    RSI/ADX/ATR keys are confirmed live (2026-07-14). MACD/BB keys are
    the brief's documented best-effort guesses, not confirmed live.
    """
    base = {
        "Date": "Tue 14 Jul '26",
        "Open": "217.04",
        "High": "222.75",
        "Low": "215.28",
        "Close": "216.10",
        "Vol": "1.64 M",
        "RSI": "45.79",
        "ADX": "13.60",
        "ATR": "23.71",
        "MACD": "1.25",
        "BB Upper": "230.00",
        "BB Lower": "210.00",
    }
    base.update(overrides)
    return {"success": True, "data": base}


def _make_fake_tv_call(read_response, timeframe_ok=True):
    """Build a fake tv_call for extract_indicators()'s call sequence:
    `chart timeframe` -> `chart openDataWindow` -> `chart read`. No
    `chart symbol` call is expected — asserts if one is made."""

    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            raise AssertionError(
                f"extract_indicators() must NOT switch chart symbol, got: {args}"
            )
        if args[:2] == ("chart", "timeframe"):
            return {"success": True} if timeframe_ok else dict(ERROR_DICT_SHAPE)
        if args == ("chart", "openDataWindow"):
            return {"success": True}
        if args == ("chart", "read"):
            return read_response
        raise AssertionError(f"Unexpected tv_call args: {args}")

    return fake_tv_call


# --- Test 1: all six target fields present and in-range ---

def test_extract_indicators_returns_all_present_valid_values(monkeypatch):
    fake = _make_fake_tv_call(_real_shaped_response())
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["rsi"] == 45.79
    assert result["macd"] == 1.25
    assert result["bb_upper"] == 230.00
    assert result["bb_lower"] == 210.00
    assert result["adx"] == 13.60
    assert result["atr"] == 23.71


# --- Test 2: RSI out of range (> 100) rejected ---

def test_extract_indicators_rejects_rsi_out_of_range(monkeypatch):
    fake = _make_fake_tv_call(_real_shaped_response(**{"RSI": "150"}))
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["rsi"] is None


# --- Test 3: RSI accepted at inclusive boundaries 0 and 100 ---

@pytest.mark.parametrize("raw", ["0", "100"])
def test_extract_indicators_accepts_rsi_at_boundaries(monkeypatch, raw):
    fake = _make_fake_tv_call(_real_shaped_response(**{"RSI": raw}))
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["rsi"] == float(raw)


# --- Test 4: negative MACD accepted (no range restriction, only finiteness) ---

def test_extract_indicators_accepts_negative_macd(monkeypatch):
    fake = _make_fake_tv_call(_real_shaped_response(**{"MACD": "-2.35"}))
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["macd"] == -2.35


# --- Test 5: non-finite or missing MACD rejected ---

def test_extract_indicators_rejects_non_finite_macd_unparseable(monkeypatch):
    fake = _make_fake_tv_call(_real_shaped_response(**{"MACD": "not-a-number"}))
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["macd"] is None


def test_extract_indicators_rejects_non_finite_macd_missing_key(monkeypatch):
    response = _real_shaped_response()
    del response["data"]["MACD"]
    fake = _make_fake_tv_call(response)
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["macd"] is None


# --- Test 6: BB upper below BB lower — both rejected ---

def test_extract_indicators_rejects_bb_upper_below_bb_lower(monkeypatch):
    fake = _make_fake_tv_call(
        _real_shaped_response(**{"BB Upper": "100", "BB Lower": "110"})
    )
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["bb_upper"] is None
    assert result["bb_lower"] is None


# --- Test 7: sane BB upper/lower pair correctly extracted ---

def test_extract_indicators_accepts_valid_bb_upper_and_lower(monkeypatch):
    fake = _make_fake_tv_call(
        _real_shaped_response(**{"BB Upper": "230.00", "BB Lower": "210.00"})
    )
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["bb_upper"] == 230.00
    assert result["bb_lower"] == 210.00


# --- Test 8: ADX out of range rejected ---

def test_extract_indicators_rejects_adx_out_of_range(monkeypatch):
    fake = _make_fake_tv_call(_real_shaped_response(**{"ADX": "150"}))
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["adx"] is None


# --- Test 9: negative ATR rejected ---

def test_extract_indicators_rejects_negative_atr(monkeypatch):
    fake = _make_fake_tv_call(_real_shaped_response(**{"ATR": "-5"}))
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["atr"] is None


# --- Test 10: missing indicator keys degrade to None, no exception ---

def test_extract_indicators_returns_none_for_missing_indicator_key(monkeypatch):
    response = {"success": True, "data": {"RSI": "45.79"}}
    fake = _make_fake_tv_call(response)
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["rsi"] == 45.79
    assert result["macd"] is None
    assert result["bb_upper"] is None
    assert result["bb_lower"] is None
    assert result["adx"] is None
    assert result["atr"] is None


# --- Test 11: falls back to alternate BB key variant ---

def test_extract_indicators_falls_back_to_alternate_bb_key_variant(monkeypatch):
    response = _real_shaped_response()
    del response["data"]["BB Upper"]
    del response["data"]["BB Lower"]
    response["data"]["Bollinger Upper"] = "230.00"
    response["data"]["Bollinger Lower"] = "210.00"
    fake = _make_fake_tv_call(response)
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result["bb_upper"] == 230.00
    assert result["bb_lower"] == 210.00


# --- Test 12: chart timeframe call failure -> all None ---

def test_extract_indicators_returns_all_none_on_timeframe_call_failure(monkeypatch):
    fake = _make_fake_tv_call(_real_shaped_response(), timeframe_ok=False)
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result == {
        "rsi": None,
        "macd": None,
        "bb_upper": None,
        "bb_lower": None,
        "adx": None,
        "atr": None,
    }


# --- Test 13: chart read call failure -> all None ---

def test_extract_indicators_returns_all_none_on_read_call_failure(monkeypatch):
    fake = _make_fake_tv_call(dict(ERROR_DICT_SHAPE))
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result == {
        "rsi": None,
        "macd": None,
        "bb_upper": None,
        "bb_lower": None,
        "adx": None,
        "atr": None,
    }


# --- Test 14: malformed `data` field (not a dict) never raises ---

@pytest.mark.parametrize("malformed_data", [["not", "a", "dict"], "just a string", None])
def test_extract_indicators_never_raises_on_malformed_data_field(monkeypatch, malformed_data):
    fake = _make_fake_tv_call({"success": True, "data": malformed_data})
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_indicators("1D")

    assert result == {
        "rsi": None,
        "macd": None,
        "bb_upper": None,
        "bb_lower": None,
        "adx": None,
        "atr": None,
    }


# --- Extra: no chart symbol switch call is ever made ---

def test_extract_indicators_never_switches_chart_symbol(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "timeframe"):
            return {"success": True}
        if args == ("chart", "openDataWindow"):
            return {"success": True}
        if args == ("chart", "read"):
            return _real_shaped_response()
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(data_window_validator, "tv_call", fake_tv_call)

    extract_indicators("1D")

    assert all(call[:2] != ("chart", "symbol") for call in calls)
    assert ("chart", "timeframe", "1D") in calls
