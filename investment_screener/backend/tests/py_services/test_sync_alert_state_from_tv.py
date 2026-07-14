"""
Task 5C-3: Alert State Sync

Tests for alert_manager.sync_alert_state(), a stateless, single-poll
classifier that reads TV's current live `alert list` response and
classifies each alert into pending/fired/expired using ONLY the real,
confirmed `active` and `last_fired` fields (never `expiration` — no
confirmed real data exists for that field's shape when an alert is
genuinely expired; see this task's brief).

Classification priority (per the brief): fired > expired > pending.
    - last_fired is not None                      -> "fired"
    - last_fired is None and active is False       -> "expired"
    - last_fired is None and active is True        -> "pending"
    - anything else (missing/malformed active)     -> "pending" (conservative)

This function does NOT persist results or compare against a prior poll
(Task 5C-4's not-yet-built persistence layer owns that) — every test here
verifies single-poll, stateless behavior only.

tv_call is mocked at the alert_manager module's imported reference — no
test here ever shells out to the real TV CDP engine, and no test ever
creates, modifies, or deletes a live TV alert.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import alert_manager  # noqa: E402
from alert_manager import sync_alert_state  # noqa: E402


def _list_response(alerts):
    return {"success": True, "alert_count": len(alerts), "alerts": alerts, "source": "internal_api"}


def _condition(price):
    """Build a real-shaped TV alert `condition` object for test fixtures.

    Matches the actual `alert list` TV CDP response shape confirmed live
    against the user's real TradingView account (2026-07-14, 306 sampled
    alerts) — a nested object, not a flat string. This task's
    classification logic doesn't read `condition` at all, but fixtures
    still include a real-shaped one to stay representative of the real
    API, matching this session's established convention.
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


# --- Test 1: pending — active True, last_fired None ---

def test_sync_alert_state_classifies_pending(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "id-pending",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "active": True,
                    "last_fired": None,
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert len(result) == 1
    assert result[0]["state"] == "pending"


# --- Test 2: fired — active True, last_fired set ---

def test_sync_alert_state_classifies_fired_when_active(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "id-fired-active",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "active": True,
                    "last_fired": "2026-07-13T12:00:00Z",
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert len(result) == 1
    assert result[0]["state"] == "fired"


# --- Test 3: fired takes priority over active=False ---

def test_sync_alert_state_classifies_fired_when_inactive(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "id-fired-inactive",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "active": False,
                    "last_fired": "2026-07-13T12:00:00Z",
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert len(result) == 1
    assert result[0]["state"] == "fired"


# --- Test 4: expired — active False, last_fired None ---

def test_sync_alert_state_classifies_expired(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "id-expired",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "active": False,
                    "last_fired": None,
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert len(result) == 1
    assert result[0]["state"] == "expired"


# --- Test 5: alert list failure degrades to [], never raises ---

def test_sync_alert_state_returns_empty_list_on_list_failure(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return dict(ERROR_DICT_SHAPE)
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert result == []


# --- Test 6: no alerts returns [] ---

def test_sync_alert_state_returns_empty_list_when_no_alerts(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert result == []


# --- Test 7: malformed entries are skipped, valid entry still classified ---

def test_sync_alert_state_skips_malformed_entry_without_crashing(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                "not-a-dict",
                {"symbol": "AAPL", "condition": _condition(200.0), "active": True, "last_fired": None},
                {
                    "alert_id": "valid-id",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "active": True,
                    "last_fired": None,
                    "created": "2026-07-13T00:00:00Z",
                },
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert len(result) == 1
    assert result[0]["alert_id"] == "valid-id"
    assert result[0]["state"] == "pending"


# --- Test 8: output shape has exact expected keys and values ---

def test_sync_alert_state_includes_alert_id_and_symbol_in_output(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "shape-id",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "active": True,
                    "last_fired": None,
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = sync_alert_state()

    assert len(result) == 1
    entry = result[0]
    assert entry == {
        "alert_id": "shape-id",
        "symbol": "NASDAQ:NVDA",
        "state": "pending",
        "last_fired": None,
        "created": "2026-07-13T00:00:00Z",
    }
