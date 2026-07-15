"""
Task 5C-1: Alert Creation

Tests for alert_manager.create_price_alert(), which composes tv_client.py's
tv_call() primitive (Task 5A-8's resilient, never-raises wrapper) to create
a TradingView price alert and correlate its real alert_id via a
create-then-list flow, since the real `alert create` CLI response contains
no alert ID (pure DOM automation — see tradingview-cdp/core/alerts.js).

tv_call is mocked at the alert_manager module's imported reference — no
test here ever shells out to the real TV CDP engine.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import alert_manager  # noqa: E402
from alert_manager import create_price_alert  # noqa: E402


def _never_call(*args, **kwargs):
    """A tv_call stand-in that fails the test loudly if ever invoked."""
    raise AssertionError(f"tv_call must not be invoked, but was called with args={args}")


def _list_response(alerts):
    return {"success": True, "alert_count": len(alerts), "alerts": alerts, "source": "internal_api"}


def _condition(price):
    """Build a real-shaped TV alert `condition` object for test fixtures.

    Matches the actual `alert list` TV CDP response shape confirmed live
    against the user's real TradingView account (2026-07-14, 306 sampled
    alerts) — a nested object, not the flat "greater_than"/"less_than"
    string the pre-bugfix tests incorrectly assumed. The price threshold
    lives at `series[1]["value"]`.
    """
    return {
        "type": "cross",
        "frequency": "on_first_fire",
        "series": [{"type": "barset"}, {"type": "value", "value": price}],
        "cross_interval": True,
        "resolution": "1",
    }


ERROR_DICT_SHAPE = {
    "error": "CDP timeout",
    "data": None,
    "cached": False,
    "timestamp": "2026-07-12T00:00:00+00:00",
}


# --- Test 1: Success path returns the correlated real alert_id ---

def test_create_price_alert_returns_id_on_success(monkeypatch):
    """A successful chart-switch + create + list, with exactly one
    matching alert in the list, returns that alert's real alert_id."""
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("alert", "create"):
            return {
                "success": True,
                "price": 500.0,
                "condition": "greater_than",
                "message": "(none)",
                "price_set": True,
                "source": "dom_fallback",
            }
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "abc123",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = create_price_alert("NVDA", 500.0, "above")

    assert result == "abc123"


# --- Test 2: direction="above" maps to --condition greater_than ---

def test_create_price_alert_maps_above_to_greater_than(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("alert", "create"):
            return {"success": True}
        if args == ("alert", "list"):
            return _list_response([
                {"alert_id": "id-1", "symbol": "NVDA", "condition": _condition(500.0)}
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    create_price_alert("NVDA", 500.0, "above")

    create_call = next(c for c in calls if c[:2] == ("alert", "create"))
    assert "--condition" in create_call
    assert create_call[create_call.index("--condition") + 1] == "greater_than"


# --- Test 3: direction="below" maps to --condition less_than ---

def test_create_price_alert_maps_below_to_less_than(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("alert", "create"):
            return {"success": True}
        if args == ("alert", "list"):
            return _list_response([
                {"alert_id": "id-2", "symbol": "NVDA", "condition": _condition(500.0)}
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    create_price_alert("NVDA", 500.0, "below")

    create_call = next(c for c in calls if c[:2] == ("alert", "create"))
    assert "--condition" in create_call
    assert create_call[create_call.index("--condition") + 1] == "less_than"


# --- Test 4: Chart switch happens before alert create ---

def test_create_price_alert_switches_chart_before_creating(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("alert", "create"):
            return {"success": True}
        if args == ("alert", "list"):
            return _list_response([
                {"alert_id": "id-3", "symbol": "NVDA", "condition": _condition(500.0)}
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    create_price_alert("NVDA", 500.0, "above")

    assert calls[0] == ("chart", "symbol", "NVDA")
    create_index = next(i for i, c in enumerate(calls) if c[:2] == ("alert", "create"))
    assert create_index > 0


# --- Test 5: Invalid direction raises ValueError, tv_call never invoked ---

def test_create_price_alert_invalid_direction_raises_value_error(monkeypatch):
    monkeypatch.setattr(alert_manager, "tv_call", _never_call)

    with pytest.raises(ValueError):
        create_price_alert("NVDA", 500.0, "sideways")


# --- Test 6: Invalid price raises ValueError, tv_call never invoked ---

def test_create_price_alert_invalid_price_raises_value_error(monkeypatch):
    monkeypatch.setattr(alert_manager, "tv_call", _never_call)

    with pytest.raises(ValueError):
        create_price_alert("NVDA", -5.0, "above")

    with pytest.raises(ValueError):
        create_price_alert("NVDA", 0, "above")


# --- Test 7: Chart-switch failure returns None, create/list never invoked ---

def test_create_price_alert_returns_none_on_chart_switch_failure(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return dict(ERROR_DICT_SHAPE)
        raise AssertionError(f"tv_call must not proceed past chart switch, got: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = create_price_alert("NVDA", 500.0, "above")

    assert result is None
    assert len(calls) == 1
    assert calls[0] == ("chart", "symbol", "NVDA")


# --- Test 8: Create failure returns None, list never invoked ---

def test_create_price_alert_returns_none_on_create_failure(monkeypatch):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("alert", "create"):
            return {"success": False, "error": "Alert dialog not found"}
        raise AssertionError(f"tv_call must not proceed past create, got: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = create_price_alert("NVDA", 500.0, "above")

    assert result is None
    assert calls[-1][:2] == ("alert", "create")


# --- Test 9: No matching alert in list returns None (not an exception) ---

def test_create_price_alert_returns_none_when_no_matching_alert_found_in_list(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("alert", "create"):
            return {"success": True}
        if args == ("alert", "list"):
            return _list_response([
                {"alert_id": "other-id", "symbol": "AAPL", "condition": _condition(500.0)}
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = create_price_alert("NVDA", 500.0, "above")

    assert result is None


# --- Test 10: Never raises on either tv_call failure shape ---

@pytest.mark.parametrize("failure_response", [
    dict(ERROR_DICT_SHAPE),
    {"success": False, "error": "Alert dialog not found"},
])
def test_create_price_alert_never_raises_on_tv_call_failure_shapes(monkeypatch, failure_response):
    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return failure_response
        raise AssertionError(f"tv_call must not proceed, got: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = create_price_alert("NVDA", 500.0, "above")

    assert result is None


# --- Extra: multiple matches picks the one with the latest 'created' ---

def test_create_price_alert_multiple_matches_picks_latest_created(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        if args[:2] == ("alert", "create"):
            return {"success": True}
        if args == ("alert", "list"):
            return _list_response([
                {"alert_id": "old-id", "symbol": "NVDA", "condition": _condition(500.0), "created": "2026-01-01T00:00:00Z"},
                {"alert_id": "new-id", "symbol": "NVDA", "condition": _condition(500.0), "created": "2026-07-13T00:00:00Z"},
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = create_price_alert("NVDA", 500.0, "above")

    assert result == "new-id"


# --- Extra: ticker validation ---

def test_create_price_alert_invalid_ticker_raises_value_error(monkeypatch):
    monkeypatch.setattr(alert_manager, "tv_call", _never_call)

    with pytest.raises(ValueError):
        create_price_alert("", 500.0, "above")


# --- Bugfix (condition-shape): _extract_condition_price / _find_created_alert_id ---
#
# The tests above exercise create_price_alert()'s end-to-end flow with
# real-shaped mock `condition` objects. These tests exercise the two
# price-matching helpers directly, confirming the fix for the bug where
# _find_created_alert_id() compared a listed alert's `condition` (a real
# nested object, confirmed live against the user's TradingView account)
# against a plain condition string, which is always False in Python and
# meant create_price_alert() could never correlate a real alert_id.


def test_extract_condition_price_reads_series_value():
    """A real-shaped `condition` object's price threshold is correctly
    extracted from `condition["series"][1]["value"]`."""
    condition = _condition(123.45)

    assert alert_manager._extract_condition_price(condition) == 123.45


@pytest.mark.parametrize("condition", [
    "greater_than",  # the OLD, wrong flat-string assumption
    {"type": "cross"},  # missing "series"
    {"type": "cross", "series": [{"type": "barset"}]},  # series too short
])
def test_extract_condition_price_returns_none_for_malformed_condition(condition):
    assert alert_manager._extract_condition_price(condition) is None


def test_find_created_alert_id_matches_on_price_within_tolerance():
    """Float round-tripping through TV's UI/API isn't guaranteed
    bit-exact, so matching allows a small tolerance (< 0.01)."""
    alerts = [
        {"alert_id": "id-tol", "symbol": "NVDA", "condition": _condition(100.004)}
    ]

    result = alert_manager._find_created_alert_id(alerts, "NVDA", 100.00)

    assert result == "id-tol"


def test_find_created_alert_id_does_not_match_different_price():
    """A same-ticker alert at a genuinely different price must not match
    — matching by ticker alone would over-match."""
    alerts = [
        {"alert_id": "id-other", "symbol": "NVDA", "condition": _condition(450.0)}
    ]

    result = alert_manager._find_created_alert_id(alerts, "NVDA", 500.0)

    assert result is None
