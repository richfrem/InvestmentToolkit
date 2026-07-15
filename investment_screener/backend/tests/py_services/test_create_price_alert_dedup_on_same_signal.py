"""
Task 5C-2: Deduplication

Tests for alert_manager.dedup_alerts(), which checks whether an alert
already exists for a (ticker, price) pair among the user's current TV
alerts, reusing Task 5C-1's already-tested primitives
(_validate_alert_input, _tv_call_succeeded, _find_created_alert_id)
directly rather than reimplementing any matching logic.

Per this task's brief (informed by 5C-1's condition-shape bugfix, commit
ea2d295): the real TV `alert list` response cannot reliably distinguish
direction ("greater_than" vs "less_than") — all 306 real alerts sampled
live have condition.type == "cross" regardless of direction. dedup_alerts()
therefore matches on (ticker, price) only; `direction` is validated (so
garbage input still raises ValueError) but does not participate in the
match.

tv_call is mocked at the alert_manager module's imported reference — no
test here ever shells out to the real TV CDP engine, and no test ever
creates, modifies, or deletes a live TV alert.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import alert_manager  # noqa: E402
from alert_manager import dedup_alerts  # noqa: E402


def _never_call(*args, **kwargs):
    """A tv_call stand-in that fails the test loudly if ever invoked."""
    raise AssertionError(f"tv_call must not be invoked, but was called with args={args}")


def _list_response(alerts):
    return {"success": True, "alert_count": len(alerts), "alerts": alerts, "source": "internal_api"}


def _condition(price):
    """Build a real-shaped TV alert `condition` object for test fixtures.

    Matches the actual `alert list` TV CDP response shape confirmed live
    against the user's real TradingView account (2026-07-14, 306 sampled
    alerts) — a nested object, not a flat "greater_than"/"less_than"
    string. The price threshold lives at `series[1]["value"]`. Using a
    flat-string shortcut here is exactly the mistake that let 5C-1's
    original bug ship undetected — never do that in these tests.
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


# --- Test 1: Match found returns the existing alert's real alert_id ---

def test_dedup_alerts_returns_existing_id_when_match_found(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "existing-id",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = dedup_alerts("NVDA", 500.0, "above")

    assert result == "existing-id"


# --- Test 2: No match returns None ---

def test_dedup_alerts_returns_none_when_no_match(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {"alert_id": "other-1", "symbol": "AAPL", "condition": _condition(500.0)},
                {"alert_id": "other-2", "symbol": "NVDA", "condition": _condition(450.0)},
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = dedup_alerts("NVDA", 500.0, "above")

    assert result is None


# --- Test 3: Read-only — dedup never calls "create", match or no-match ---

@pytest.mark.parametrize("alerts_fixture,ticker,price,direction", [
    ([{"alert_id": "id-1", "symbol": "NVDA", "condition": _condition(500.0)}], "NVDA", 500.0, "above"),
    ([{"alert_id": "id-2", "symbol": "AAPL", "condition": _condition(200.0)}], "NVDA", 500.0, "below"),
])
def test_dedup_alerts_never_calls_create(monkeypatch, alerts_fixture, ticker, price, direction):
    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        if "create" in args:
            raise AssertionError(f"dedup_alerts must never call create, got args={args}")
        if args == ("alert", "list"):
            return _list_response(alerts_fixture)
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    dedup_alerts(ticker, price, direction)

    assert all("create" not in c for c in calls)


# --- Test 4: Invalid direction raises ValueError, tv_call never invoked ---

def test_dedup_alerts_invalid_direction_raises_value_error(monkeypatch):
    monkeypatch.setattr(alert_manager, "tv_call", _never_call)

    with pytest.raises(ValueError):
        dedup_alerts("NVDA", 500.0, "sideways")


# --- Test 5: Invalid price raises ValueError, tv_call never invoked ---

def test_dedup_alerts_invalid_price_raises_value_error(monkeypatch):
    monkeypatch.setattr(alert_manager, "tv_call", _never_call)

    with pytest.raises(ValueError):
        dedup_alerts("NVDA", -1.0, "above")


# --- Test 6: alert list failure degrades to None, never raises ---

def test_dedup_alerts_returns_none_on_list_failure(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return dict(ERROR_DICT_SHAPE)
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = dedup_alerts("NVDA", 500.0, "above")

    assert result is None


# --- Test 7: Matches within _find_created_alert_id's price tolerance ---

def test_dedup_alerts_matches_within_price_tolerance(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {"alert_id": "tol-id", "symbol": "NVDA", "condition": _condition(100.004)}
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = dedup_alerts("NVDA", 100.00, "above")

    assert result == "tol-id"
