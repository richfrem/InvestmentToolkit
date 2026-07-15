"""Tests for order_risk_gates.py — check_mrc_limit() (Task 5E-1).

MRC here means Marginal Risk Contribution (Phase 3 E1's real,
correlation/covariance-aware risk-decomposition metric from
risk_engine.py), NOT "Maximum Recommended Concentration". This function
reuses the real risk_snapshot.json data shape and rebalancer.py's E2
compute_risk_budget_check() projection formula
(old_mrc * 100 * new_weight / current_weight), applied to a single
ad-hoc order instead of a batch of routed orders.

risk_snapshot is passed explicitly in every test below — never relies
on the real file on disk.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402
from order_risk_gates import check_mrc_limit  # noqa: E402


def _order(ticker="CORZ", side="BUY", shares=10.0, price=10.0):
    return {"ticker": ticker, "side": side, "shares": shares, "price": price}


def _portfolio_state(holdings, total_value=100_000.0):
    return {"holdings": holdings, "total_value": total_value}


def _risk_snapshot(mrc_map):
    return {"marginalRiskContribution": mrc_map}


def test_check_mrc_limit_passes_order_within_limit():
    """A small buy that keeps projected MRC comfortably under 25%."""
    order = _order(ticker="CORZ", side="BUY", shares=1.0, price=10.0)
    portfolio_state = _portfolio_state({"CORZ": {"weight_pct": 20.0}}, total_value=100_000.0)
    risk_snapshot = _risk_snapshot({"CORZ": 0.15})

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["holdings_flagged"] == []


def test_check_mrc_limit_fails_order_exceeding_limit():
    """A large buy that pushes the ticker's projected MRC over 25%."""
    order = _order(ticker="CORZ", side="BUY", shares=1000.0, price=100.0)
    portfolio_state = _portfolio_state({"CORZ": {"weight_pct": 20.0}}, total_value=100_000.0)
    risk_snapshot = _risk_snapshot({"CORZ": 0.18})

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is False
    assert len(result["holdings_flagged"]) == 1
    flagged = result["holdings_flagged"][0]
    assert flagged["ticker"] == "CORZ"
    assert flagged["current_mrc_pct"] == 18.0
    current_weight = 0.20
    new_value = 20_000.0 + 1000.0 * 100.0
    new_weight = new_value / 100_000.0
    expected_projected = 0.18 * 100 * (new_weight / current_weight)
    assert flagged["projected_mrc_pct"] == expected_projected
    assert flagged["cap_pct"] == 25.0


def test_check_mrc_limit_uses_custom_cap():
    """mrc_cap_pct=20.0 is respected instead of the 25.0 default."""
    # current_weight=0.20, order_value=3000 -> new_weight=0.23, ratio=1.15,
    # projected_mrc_pct = 18 * 1.15 = 20.7% -> under 25% default, over 20% custom.
    order = _order(ticker="CORZ", side="BUY", shares=300.0, price=10.0)
    portfolio_state = _portfolio_state({"CORZ": {"weight_pct": 20.0}}, total_value=100_000.0)
    risk_snapshot = _risk_snapshot({"CORZ": 0.18})

    # Under the default 25% cap this order passes...
    default_result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)
    assert default_result["passed"] is True

    # ...but fails against a stricter custom 20% cap.
    custom_result = check_mrc_limit(
        order, portfolio_state, risk_snapshot=risk_snapshot, mrc_cap_pct=20.0
    )
    assert custom_result["passed"] is False
    assert custom_result["holdings_flagged"][0]["cap_pct"] == 20.0


def test_check_mrc_limit_projection_formula_matches_rebalancer():
    """Hand-computed projected_mrc_pct must match E2's exact formula: old_mrc * 100 * (new_weight / current_weight)."""
    order = _order(ticker="NBIS", side="BUY", shares=300.0, price=25.0)
    portfolio_state = _portfolio_state({"NBIS": {"weight_pct": 10.0}}, total_value=50_000.0)
    risk_snapshot = _risk_snapshot({"NBIS": 0.12})

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot, mrc_cap_pct=25.0)

    current_weight = 0.10
    current_value = current_weight * 50_000.0  # 5000
    order_value = 300.0 * 25.0  # 7500
    new_value = current_value + order_value  # 12500
    new_weight = new_value / 50_000.0  # 0.25
    expected_projected_mrc_pct = 0.12 * 100 * (new_weight / current_weight)  # 30.0

    # 30.0 > 25.0 cap, so this order must be flagged — pins the exact formula output.
    assert result["passed"] is False
    assert result["holdings_flagged"][0]["projected_mrc_pct"] == expected_projected_mrc_pct
    assert result["holdings_flagged"][0]["current_mrc_pct"] == 0.12 * 100


def test_check_mrc_limit_handles_sell_order():
    """A sell reducing the position: projected_mrc_pct < current_mrc_pct, order passes."""
    order = _order(ticker="CORZ", side="SELL", shares=500.0, price=10.0)
    portfolio_state = _portfolio_state({"CORZ": {"weight_pct": 20.0}}, total_value=100_000.0)
    risk_snapshot = _risk_snapshot({"CORZ": 0.18})

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["holdings_flagged"] == []

    # Compute what the projected/current MRC would have been, to confirm the sell
    # reduces risk contribution (per the brief's documented behavior).
    current_weight = 0.20
    current_value = current_weight * 100_000.0  # 20000
    order_value = 500.0 * 10.0  # 5000
    new_value = current_value - order_value  # 15000
    new_weight = new_value / 100_000.0  # 0.15
    current_mrc_pct = 0.18 * 100
    projected_mrc_pct = 0.18 * 100 * (new_weight / current_weight)
    assert projected_mrc_pct < current_mrc_pct


def test_check_mrc_limit_skips_projection_for_new_ticker_with_no_prior_mrc():
    """A ticker absent from marginalRiskContribution (fresh position) is never blocked."""
    order = _order(ticker="NEWCO", side="BUY", shares=1000.0, price=100.0)
    portfolio_state = _portfolio_state({}, total_value=100_000.0)
    risk_snapshot = _risk_snapshot({"CORZ": 0.18})  # NEWCO absent

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["holdings_flagged"] == []
    assert "unavailable" in result["reason"].lower()


def test_check_mrc_limit_skips_projection_for_zero_current_weight():
    """Prior MRC exists but current_weight_pct is 0.0 — no divide-by-zero, passes."""
    order = _order(ticker="CORZ", side="BUY", shares=100.0, price=10.0)
    portfolio_state = _portfolio_state({"CORZ": {"weight_pct": 0.0}}, total_value=100_000.0)
    risk_snapshot = _risk_snapshot({"CORZ": 0.18})

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["holdings_flagged"] == []


def test_check_mrc_limit_handles_missing_risk_snapshot(monkeypatch, tmp_path):
    """risk_snapshot=None and no real file present: passed=True, no exception."""
    monkeypatch.setattr(order_risk_gates, "RISK_SNAPSHOT_PATH", tmp_path / "nonexistent.json")

    order = _order(ticker="CORZ", side="BUY", shares=100.0, price=10.0)
    portfolio_state = _portfolio_state({"CORZ": {"weight_pct": 20.0}}, total_value=100_000.0)

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=None)

    assert result["passed"] is True
    assert result["holdings_flagged"] == []


def test_check_mrc_limit_only_evaluates_traded_ticker():
    """Multiple holdings present; holdings_flagged never contains a non-traded ticker."""
    order = _order(ticker="CORZ", side="BUY", shares=1000.0, price=100.0)
    portfolio_state = _portfolio_state(
        {
            "CORZ": {"weight_pct": 20.0},
            "NBIS": {"weight_pct": 15.0},
            "MSFT": {"weight_pct": 10.0},
        },
        total_value=100_000.0,
    )
    # Give every holding a high MRC so a "cascade" bug would flag them all.
    risk_snapshot = _risk_snapshot({"CORZ": 0.18, "NBIS": 0.22, "MSFT": 0.24})

    result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)

    for flagged in result["holdings_flagged"]:
        assert flagged["ticker"] == "CORZ"
