"""Tests for order_risk_gates.py — check_cluster_variance() (Task 5E-2).

This gate matches the real, already-shipped rebalancer.py
compute_risk_budget_check() (Phase 3 E2) cluster-variance check exactly:
it does NOT project a post-order variance increase — it only checks
whether the pillar's CURRENT clusterExposure["varianceContributionPct"]
(Phase 3 E1's compute_cluster_exposure() output) already exceeds the
cap, for ANY buy order in that pillar, regardless of order size. SELL
orders are never flagged, matching E2's own real scope (E2 only
evaluates "buy" actions for this check).

risk_snapshot is passed explicitly in every test below — never relies
on the real file on disk.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402
from order_risk_gates import check_cluster_variance  # noqa: E402


def _order(ticker="CORZ", side="BUY", shares=10.0, price=10.0):
    return {"ticker": ticker, "side": side, "shares": shares, "price": price}


def _portfolio_state(holdings):
    return {"holdings": holdings}


def _risk_snapshot(cluster_exposure):
    return {"clusterExposure": cluster_exposure}


def test_check_cluster_variance_passes_when_pillar_under_cap():
    """Pillar's varianceContributionPct is below the 60% default cap."""
    order = _order(ticker="CORZ", side="BUY")
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "asi_race"}})
    risk_snapshot = _risk_snapshot(
        [{"pillarId": "asi_race", "weight": 0.30, "varianceContributionPct": 45.0}]
    )

    result = check_cluster_variance(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["pillar"] == "asi_race"
    assert result["variance_pct"] == 45.0


def test_check_cluster_variance_fails_when_pillar_over_cap():
    """Pillar's varianceContributionPct exceeds the 60% default cap."""
    order = _order(ticker="CORZ", side="BUY")
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "asi_race"}})
    risk_snapshot = _risk_snapshot(
        [{"pillarId": "asi_race", "weight": 0.65, "varianceContributionPct": 72.5}]
    )

    result = check_cluster_variance(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is False
    assert result["pillar"] == "asi_race"
    assert result["variance_pct"] == 72.5
    assert "asi_race" in result["reason"]
    assert "72.5" in result["reason"]


def test_check_cluster_variance_uses_custom_cap():
    """cluster_cap_pct=50.0 is respected instead of the 60.0 default."""
    order = _order(ticker="CORZ", side="BUY")
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "asi_race"}})
    risk_snapshot = _risk_snapshot(
        [{"pillarId": "asi_race", "weight": 0.55, "varianceContributionPct": 55.0}]
    )

    # Under the default 60% cap this pillar passes...
    default_result = check_cluster_variance(order, portfolio_state, risk_snapshot=risk_snapshot)
    assert default_result["passed"] is True

    # ...but fails against a stricter custom 50% cap.
    custom_result = check_cluster_variance(
        order, portfolio_state, risk_snapshot=risk_snapshot, cluster_cap_pct=50.0
    )
    assert custom_result["passed"] is False
    assert custom_result["variance_pct"] == 55.0


def test_check_cluster_variance_never_projects_a_post_order_increase():
    """SMALL and LARGE orders for the SAME over-cap pillar produce identical results.

    Proves no order-size-dependent projection happens — the check is
    purely "is the pillar already over cap," matching E2's real
    behavior, not a scaled simulation (unlike 5E-1's MRC gate).
    """
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "asi_race"}})
    risk_snapshot = _risk_snapshot(
        [{"pillarId": "asi_race", "weight": 0.65, "varianceContributionPct": 80.0}]
    )

    small_order = _order(ticker="CORZ", side="BUY", shares=1.0, price=10.0)
    large_order = _order(ticker="CORZ", side="BUY", shares=100_000.0, price=500.0)

    small_result = check_cluster_variance(small_order, portfolio_state, risk_snapshot=risk_snapshot)
    large_result = check_cluster_variance(large_order, portfolio_state, risk_snapshot=risk_snapshot)

    assert small_result["passed"] is False
    assert large_result["passed"] is False
    assert small_result["variance_pct"] == large_result["variance_pct"] == 80.0
    assert small_result["reason"] == large_result["reason"]


def test_check_cluster_variance_sell_orders_never_flagged():
    """A SELL order for a ticker in an over-cap pillar always passes."""
    order = _order(ticker="CORZ", side="SELL", shares=500.0, price=10.0)
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "asi_race"}})
    risk_snapshot = _risk_snapshot(
        [{"pillarId": "asi_race", "weight": 0.80, "varianceContributionPct": 95.0}]
    )

    result = check_cluster_variance(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["pillar"] is None
    assert result["variance_pct"] is None


def test_check_cluster_variance_unassigned_ticker_falls_back_gracefully():
    """A ticker with no pillar_id in portfolio_state falls back to 'unassigned'."""
    order = _order(ticker="NEWCO", side="BUY")
    portfolio_state = _portfolio_state({})  # NEWCO absent entirely
    risk_snapshot = _risk_snapshot(
        [{"pillarId": "asi_race", "weight": 0.65, "varianceContributionPct": 80.0}]
        # no "unassigned" entry present
    )

    result = check_cluster_variance(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["pillar"] == "unassigned"
    assert result["variance_pct"] is None


def test_check_cluster_variance_handles_missing_risk_snapshot(monkeypatch, tmp_path):
    """risk_snapshot=None and no real file present: passed=True, no exception."""
    monkeypatch.setattr(order_risk_gates, "RISK_SNAPSHOT_PATH", tmp_path / "nonexistent.json")

    order = _order(ticker="CORZ", side="BUY")
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "asi_race"}})

    result = check_cluster_variance(order, portfolio_state, risk_snapshot=None)

    assert result["passed"] is True


def test_check_cluster_variance_pillar_with_no_cluster_entry_returns_true():
    """Ticker's pillar exists in portfolio_state but has no matching clusterExposure entry."""
    order = _order(ticker="CORZ", side="BUY")
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "quantum_computing"}})
    risk_snapshot = _risk_snapshot(
        [{"pillarId": "asi_race", "weight": 0.65, "varianceContributionPct": 80.0}]
        # no "quantum_computing" entry present
    )

    result = check_cluster_variance(order, portfolio_state, risk_snapshot=risk_snapshot)

    assert result["passed"] is True
    assert result["pillar"] == "quantum_computing"
    assert result["variance_pct"] is None


def test_check_cluster_variance_reuses_load_risk_snapshot_helper(monkeypatch):
    """Confirms check_cluster_variance() calls the SAME _load_risk_snapshot() 5E-1 defined."""
    calls = []

    def fake_load_risk_snapshot():
        calls.append(1)
        return {"clusterExposure": [{"pillarId": "asi_race", "varianceContributionPct": 10.0}]}

    monkeypatch.setattr(order_risk_gates, "_load_risk_snapshot", fake_load_risk_snapshot)

    order = _order(ticker="CORZ", side="BUY")
    portfolio_state = _portfolio_state({"CORZ": {"pillar_id": "asi_race"}})

    result = check_cluster_variance(order, portfolio_state, risk_snapshot=None)

    assert len(calls) == 1
    assert result["passed"] is True
