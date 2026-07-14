"""
Task 5D-1: Data Window Reader

Tests for data_window_validator.extract_data_window(), which composes
tv_client.py's tv_call() (Task 5A-8's resilient, never-raises wrapper) to
switch the active TV chart, open the Data Window, read it, and parse
OHLCV out of the real DOM-scraped, string-keyed dict response.

The real `chart read` response (confirmed live, 2026-07-14, read-only
check against the user's connected TradingView Desktop) is a flat dict
of raw DOM text strings whose exact key set varies with which indicators
are loaded on the chart — NOT a structured {open, high, low, close,
volume} object. This test file's fixtures use that real confirmed shape
throughout (e.g. {"Open": "217.04", "High": "222.75", "Low": "215.28",
"Close": "216.10", "Vol": "1.64 M"}), never a shortcut typed dict.

tv_call is mocked at the data_window_validator module's imported
reference — no test here ever shells out to the real TV CDP engine.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import data_window_validator  # noqa: E402
from data_window_validator import extract_data_window  # noqa: E402


ERROR_DICT_SHAPE = {
    "error": "CDP timeout",
    "data": None,
    "cached": False,
    "timestamp": "2026-07-12T00:00:00+00:00",
}


def _real_shaped_response(**overrides):
    """A real-shaped `chart read` response (confirmed live 2026-07-14).

    Every value is a raw DOM-scraped string. Callers override/omit keys
    to simulate incomplete reads.
    """
    base = {
        "Date": "Tue 14 Jul '26",
        "Open": "217.04",
        "High": "222.75",
        "Low": "215.28",
        "Close": "216.10",
        "Vol": "1.64 M",
        "Volume MA": "16.97 M",
        "EMA Fast": "229.47",
        "RSI": "45.79",
    }
    base.update(overrides)
    return {"success": True, "data": base}


def _open_window_response():
    return {"success": True}


def _make_fake_tv_call(read_responses, chart_ok=True, timeframe_ok=True):
    """Build a fake tv_call that returns a fixed sequence of `chart read`
    responses (one per invocation), and simple success stubs for the
    symbol/timeframe/openDataWindow calls."""
    calls = {"read_index": 0}

    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return {"success": True} if chart_ok else dict(ERROR_DICT_SHAPE)
        if args[:2] == ("chart", "timeframe"):
            return {"success": True} if timeframe_ok else dict(ERROR_DICT_SHAPE)
        if args == ("chart", "openDataWindow"):
            return _open_window_response()
        if args == ("chart", "read"):
            idx = calls["read_index"]
            calls["read_index"] += 1
            if idx < len(read_responses):
                return read_responses[idx]
            return read_responses[-1]
        raise AssertionError(f"Unexpected tv_call args: {args}")

    return fake_tv_call


# --- Test 1: returns a parsed OHLCV dict on a complete real-shaped response ---

def test_extract_data_window_returns_ohlcv_dict(monkeypatch):
    fake = _make_fake_tv_call([_real_shaped_response()])
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_data_window("NVDA")

    assert result is not None
    assert result["open"] == 217.04
    assert result["high"] == 222.75
    assert result["low"] == 215.28
    assert result["close"] == 216.10
    assert result["volume"] == 1_640_000
    assert "timestamp" in result


# --- Test 2: custom timeframe passed through unmodified ---

def test_extract_data_window_with_custom_timeframe(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("chart", "timeframe"):
            return {"success": True}
        if args == ("chart", "openDataWindow"):
            return _open_window_response()
        if args == ("chart", "read"):
            return _real_shaped_response()
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(data_window_validator, "tv_call", fake_tv_call)

    extract_data_window("NVDA", timeframe="60")

    assert ("chart", "timeframe", "60") in calls


# --- Test 3: call order is symbol -> timeframe -> openDataWindow -> read ---

def test_extract_data_window_switches_symbol_before_reading(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("chart", "timeframe"):
            return {"success": True}
        if args == ("chart", "openDataWindow"):
            return _open_window_response()
        if args == ("chart", "read"):
            return _real_shaped_response()
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(data_window_validator, "tv_call", fake_tv_call)

    extract_data_window("NVDA", timeframe="1D")

    assert calls[0] == ("chart", "symbol", "NVDA")
    assert calls[1] == ("chart", "timeframe", "1D")
    assert calls[2] == ("chart", "openDataWindow")
    assert calls[3] == ("chart", "read")


# --- Test 4: retries once on incomplete data (missing Close), then succeeds ---

def test_extract_data_window_retries_on_incomplete_data_then_succeeds(monkeypatch):
    incomplete = _real_shaped_response()
    del incomplete["data"]["Close"]
    complete = _real_shaped_response()

    fake = _make_fake_tv_call([incomplete, complete])
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    sleep_calls = []
    monkeypatch.setattr(data_window_validator.time, "sleep", lambda s: sleep_calls.append(s))

    result = extract_data_window("NVDA")

    assert result is not None
    assert result["close"] == 216.10
    assert sleep_calls == [1]


# --- Test 5: exponential backoff sequence is 1, 2, 4, 8 across 5 attempts ---

def test_extract_data_window_exponential_backoff_intervals(monkeypatch):
    incomplete = _real_shaped_response()
    del incomplete["data"]["Close"]

    fake = _make_fake_tv_call([incomplete] * 5)
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    sleep_calls = []
    monkeypatch.setattr(data_window_validator.time, "sleep", lambda s: sleep_calls.append(s))

    extract_data_window("NVDA")

    assert sleep_calls == [1, 2, 4, 8]


# --- Test 6: returns last-known-good result after later attempts degrade ---

def test_extract_data_window_returns_last_known_good_after_exhausting_retries(monkeypatch):
    complete = _real_shaped_response()
    incomplete = _real_shaped_response()
    del incomplete["data"]["Open"]

    fake = _make_fake_tv_call([complete, incomplete, incomplete, incomplete, incomplete])
    monkeypatch.setattr(data_window_validator, "tv_call", fake)
    monkeypatch.setattr(data_window_validator.time, "sleep", lambda s: None)

    result = extract_data_window("NVDA")

    assert result is not None
    assert result["open"] == 217.04
    assert result["close"] == 216.10


# --- Test 7: returns None when every attempt's underlying tv_call fails
# outright (not merely an incomplete-but-successful read) ---
#
# Per the brief's pseudocode, last_known_good is set to ANY non-None
# _attempt_extract() result — even a structurally incomplete one (missing
# O/H/L/C) — since the read itself still succeeded. It only stays None
# across every attempt if the underlying tv_call (chart read) fails
# outright each time, so _attempt_extract() itself returns None on every
# attempt.

def test_extract_data_window_returns_none_when_never_complete(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("chart", "timeframe"):
            return {"success": True}
        if args == ("chart", "openDataWindow"):
            return _open_window_response()
        if args == ("chart", "read"):
            return dict(ERROR_DICT_SHAPE)
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(data_window_validator, "tv_call", fake_tv_call)
    monkeypatch.setattr(data_window_validator.time, "sleep", lambda s: None)

    result = extract_data_window("NVDA")

    assert result is None


# --- Test 8: _parse_volume handles K/M/B suffixes, never raises ---

@pytest.mark.parametrize("raw,expected", [
    ("500", 500),
    ("1.5 K", 1500),
    ("1.64 M", 1_640_000),
    ("2 B", 2_000_000_000),
    ("not-a-number", None),
])
def test_parse_volume_handles_k_m_b_suffixes(raw, expected):
    assert data_window_validator._parse_volume(raw) == expected


# --- Test 9: falls back to "Volume" key when "Vol" is absent ---

def test_extract_data_window_falls_back_to_alternate_volume_key(monkeypatch):
    response = _real_shaped_response()
    del response["data"]["Vol"]
    response["data"]["Volume"] = "1.64 M"

    fake = _make_fake_tv_call([response])
    monkeypatch.setattr(data_window_validator, "tv_call", fake)

    result = extract_data_window("NVDA")

    assert result is not None
    assert result["volume"] == 1_640_000


# --- Test 10: never raises when chart symbol switch fails on every attempt ---

def test_extract_data_window_never_raises_on_chart_call_failure(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return dict(ERROR_DICT_SHAPE)
        raise AssertionError(f"tv_call must not proceed past chart switch, got: {args}")

    monkeypatch.setattr(data_window_validator, "tv_call", fake_tv_call)
    monkeypatch.setattr(data_window_validator.time, "sleep", lambda s: None)

    result = extract_data_window("NVDA")

    assert result is None


# --- Extra: _parse_price handles comma thousands separators, never raises ---

@pytest.mark.parametrize("raw,expected", [
    ("217.04", 217.04),
    ("1,234.56", 1234.56),
    (None, None),
    ("garbage", None),
])
def test_parse_price_handles_commas_and_never_raises(raw, expected):
    assert data_window_validator._parse_price(raw) == expected


# --- Extra: _first_present returns the first matching key's value ---

def test_first_present_returns_first_matching_key():
    data = {"Volume": "1.64 M"}
    assert data_window_validator._first_present(data, ["Vol", "Volume", "V"]) == "1.64 M"


def test_first_present_returns_none_when_no_key_present():
    data = {"Open": "217.04"}
    assert data_window_validator._first_present(data, ["Vol", "Volume", "V"]) is None
