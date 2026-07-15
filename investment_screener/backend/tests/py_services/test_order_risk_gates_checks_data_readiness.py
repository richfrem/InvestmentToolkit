"""Tests for order_risk_gates.py — check_data_readiness_gate() (5E-fix).

This gate closes the previously-orphaned Task 5D-8 -> Task 5E integration:
data_window_validator.py's check_order_data_readiness() was fully built and
unit-tested but had zero production callers — its own docstring literally
says it's "designed to be imported and called FROM [order_risk_gates.py]
once it exists." This gate is that missing caller.

Only the RSI-overbought veto ("rsi_veto") actually gates (fails) an order —
a low liquidity_score is informational only, surfaced in every result
regardless of pass/fail, matching 5D-8's own docstring distinction between
"reports data" (liquidity) and "gates" (RSI veto only).

The live check_order_data_readiness() import is a genuine external-system
boundary (live TV CDP chart-switch) — monkeypatched at the
data_window_validator module's own reference (same pattern already
established in test_data_window_integration_with_order_gates.py), never via
unittest.mock. All other cases pass a real, constructed data_readiness dict
directly (dependency injection), matching this module's existing convention
for daily_volume=/questrade_cash=.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import data_window_validator  # noqa: E402
import order_risk_gates  # noqa: E402
from order_risk_gates import check_data_readiness_gate  # noqa: E402


def _order(side="BUY", ticker="CORZ"):
    return {"ticker": ticker, "side": side, "shares": 10.0, "price": 100.0}


def test_sell_order_always_passes():
    """SELL orders are never gated — matches this module's BUY-only convention
    for cluster_variance/breaker_veto (5E-2/5E-3)."""
    order = _order(side="SELL")

    result = check_data_readiness_gate(order, data_readiness={"rsi_veto": {"vetoed": True}})

    assert result["passed"] is True
    assert result["rsi"] is None
    assert result["liquidity_score"] is None


def test_buy_with_rsi_veto_fails_and_surfaces_liquidity_score():
    """A vetoed rsi_veto fails the gate; liquidity_score is surfaced even though
    it did not itself cause the failure."""
    order = _order()
    data_readiness = {
        "rsi_veto": {"vetoed": True, "reason": "RSI 85.0 >= 80.0 (overbought)", "rsi": 85.0},
        "liquidity": {"score": 0.2, "volume": 50_000, "range_pct": 1.0},
    }

    result = check_data_readiness_gate(order, data_readiness=data_readiness)

    assert result["passed"] is False
    assert "RSI 85.0" in result["reason"]
    assert result["rsi"] == 85.0
    assert result["liquidity_score"] == 0.2


def test_buy_without_rsi_veto_passes_and_still_surfaces_liquidity_score():
    """vetoed=False passes, but liquidity_score is still surfaced (informational,
    never gates on its own — a low score does not fail this gate)."""
    order = _order()
    data_readiness = {
        "rsi_veto": {"vetoed": False, "reason": None, "rsi": 45.0},
        "liquidity": {"score": 0.2, "volume": 50_000, "range_pct": 1.0},
    }

    result = check_data_readiness_gate(order, data_readiness=data_readiness)

    assert result["passed"] is True
    assert result["rsi"] == 45.0
    assert result["liquidity_score"] == 0.2


def test_buy_with_missing_data_readiness_keys_degrades_to_pass():
    """An empty/malformed data_readiness dict (no rsi_veto/liquidity keys at
    all) degrades to passed=True with None fields — never raises."""
    order = _order()

    result = check_data_readiness_gate(order, data_readiness={})

    assert result["passed"] is True
    assert result["rsi"] is None
    assert result["liquidity_score"] is None


def test_buy_with_data_readiness_none_fetches_live_and_handles_error(monkeypatch):
    """data_readiness=None triggers a lazy import + call of
    data_window_validator.check_order_data_readiness() — the live TV CDP
    boundary. If that call raises, the gate itself never raises: it degrades
    to passed=True (defense-in-depth specific to this one gate's live I/O,
    unlike the pure-file-read gates elsewhere in this module)."""

    def _raising_check_order_data_readiness(ticker, rsi_veto_threshold=80.0):
        raise RuntimeError("simulated live TV CDP failure")

    monkeypatch.setattr(
        data_window_validator, "check_order_data_readiness", _raising_check_order_data_readiness
    )
    order = _order()

    result = check_data_readiness_gate(order, data_readiness=None)

    assert result["passed"] is True
    assert result["rsi"] is None
    assert result["liquidity_score"] is None


def test_buy_with_data_readiness_none_fetches_live_and_succeeds(monkeypatch):
    """data_readiness=None with a successful live call uses its result."""

    def _fake_check_order_data_readiness(ticker, rsi_veto_threshold=80.0):
        assert ticker == "CORZ"
        return {
            "rsi_veto": {"vetoed": True, "reason": "RSI 90.0 >= 80.0 (overbought)", "rsi": 90.0},
            "liquidity": {"score": 1.0, "volume": 2_000_000, "range_pct": 2.0},
        }

    monkeypatch.setattr(
        data_window_validator, "check_order_data_readiness", _fake_check_order_data_readiness
    )
    order = _order()

    result = check_data_readiness_gate(order, data_readiness=None)

    assert result["passed"] is False
    assert result["rsi"] == 90.0
    assert result["liquidity_score"] == 1.0
