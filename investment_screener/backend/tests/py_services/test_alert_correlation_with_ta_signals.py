"""
Task 5C-7: Alert Correlation

Tests for alert_manager.get_alerts_for_ticker() and
alert_manager.score_alert_correlation().

get_alerts_for_ticker(ticker) lists a ticker's real TV alerts (filtered
by case-insensitive substring match on `symbol`, same convention as
_find_created_alert_id()), enriched with `_extract_condition_price()`
(5C-1) and `_classify_alert_state()` (5C-3) — reused unchanged.

score_alert_correlation(alert, current_price, ta_signal=None) scores one
alert's relevance given a caller-supplied current price and optional
TA-band context. This module deliberately does NOT fetch price or TA
data itself (see this task's brief) — both are caller-supplied
parameters, avoiding a new fragile cross-module dependency on
market_data.py/technicals.py.

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
from alert_manager import get_alerts_for_ticker, score_alert_correlation  # noqa: E402


def _list_response(alerts):
    return {"success": True, "alert_count": len(alerts), "alerts": alerts, "source": "internal_api"}


def _condition(price):
    """Build a real-shaped TV alert `condition` object for test fixtures.

    Matches the actual `alert list` TV CDP response shape confirmed live
    against the user's real TradingView account (2026-07-14, 306 sampled
    alerts) — a nested object, not a flat string.
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


# --- Test 1: matching alert is returned enriched with price + state ---

def test_get_alerts_for_ticker_returns_matching_alerts_enriched(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "id-nvda",
                    "symbol": "NASDAQ:NVDA",
                    "condition": _condition(500.0),
                    "active": True,
                    "last_fired": None,
                    "created": "2026-07-13T00:00:00Z",
                }
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = get_alerts_for_ticker("NVDA")

    assert result == [
        {
            "alert_id": "id-nvda",
            "symbol": "NASDAQ:NVDA",
            "price": 500.0,
            "state": "pending",
        }
    ]


# --- Test 2: non-matching tickers are filtered out ---

def test_get_alerts_for_ticker_filters_out_non_matching_tickers(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                {
                    "alert_id": "id-aapl",
                    "symbol": "NASDAQ:AAPL",
                    "condition": _condition(200.0),
                    "active": True,
                    "last_fired": None,
                    "created": "2026-07-13T00:00:00Z",
                },
                {
                    "alert_id": "id-msft",
                    "symbol": "NASDAQ:MSFT",
                    "condition": _condition(300.0),
                    "active": True,
                    "last_fired": None,
                    "created": "2026-07-13T00:00:00Z",
                },
            ])
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = get_alerts_for_ticker("NVDA")

    assert result == []


# --- Test 3: alert list failure degrades to [], never raises ---

def test_get_alerts_for_ticker_returns_empty_list_on_list_failure(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return dict(ERROR_DICT_SHAPE)
        raise AssertionError(f"Unexpected tv_call args: {args}")

    monkeypatch.setattr(alert_manager, "tv_call", fake_tv_call)

    result = get_alerts_for_ticker("NVDA")

    assert result == []


# --- Test 4: malformed entries are skipped, valid entry still returned ---

def test_get_alerts_for_ticker_skips_malformed_entry_without_crashing(monkeypatch):
    def fake_tv_call(*args, **kwargs):
        if args == ("alert", "list"):
            return _list_response([
                "not-a-dict",
                {"symbol": "NASDAQ:NVDA", "condition": _condition(500.0), "active": True, "last_fired": None},
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

    result = get_alerts_for_ticker("NVDA")

    assert len(result) == 1
    assert result[0]["alert_id"] == "valid-id"


# --- Test 5: proximity_pct computed correctly ---

def test_score_alert_correlation_computes_proximity_pct():
    alert = {"alert_id": "id-1", "symbol": "NASDAQ:NVDA", "price": 100.0, "state": "pending"}

    result = score_alert_correlation(alert, current_price=95.0)

    assert result["proximity_pct"] == 5.0


# --- Test 6: matches_ta_signal True for actionable bands ---

def test_score_alert_correlation_matches_ta_signal_for_actionable_band():
    alert = {"alert_id": "id-1", "symbol": "NASDAQ:NVDA", "price": 100.0, "state": "pending"}

    for band in ("ACCUMULATE", "EXIT", "REDUCE"):
        result = score_alert_correlation(alert, current_price=100.0, ta_signal={"band": band})
        assert result["matches_ta_signal"] is True, f"expected True for band={band}"


# --- Test 7: matches_ta_signal False for non-actionable band ---

def test_score_alert_correlation_does_not_match_non_actionable_band():
    alert = {"alert_id": "id-1", "symbol": "NASDAQ:NVDA", "price": 100.0, "state": "pending"}

    result = score_alert_correlation(alert, current_price=100.0, ta_signal={"band": "HOLD"})

    assert result["matches_ta_signal"] is False


# --- Test 8: missing ta_signal degrades to False, never raises ---

def test_score_alert_correlation_handles_missing_ta_signal():
    alert = {"alert_id": "id-1", "symbol": "NASDAQ:NVDA", "price": 100.0, "state": "pending"}

    result = score_alert_correlation(alert, current_price=100.0, ta_signal=None)

    assert result["matches_ta_signal"] is False


# --- Test 9: missing alert price returns None proximity, never raises ---

def test_score_alert_correlation_returns_none_proximity_when_alert_price_missing():
    alert = {"alert_id": "id-1", "symbol": "NASDAQ:NVDA", "price": None, "state": "pending"}

    result = score_alert_correlation(alert, current_price=100.0)

    assert result["proximity_pct"] is None
