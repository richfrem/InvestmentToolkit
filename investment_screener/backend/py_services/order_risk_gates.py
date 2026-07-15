"""
Order Risk Gates — MRC Risk Gate (Task 5E-1)

Checks whether a single, ad-hoc order would push its ticker's real
Marginal Risk Contribution (MRC) — Phase 3 E1's correlation/covariance-
aware risk-decomposition metric from risk_engine.py's
compute_marginal_risk_contribution() — over the portfolio's real risk
budget cap. "MRC" here is Marginal Risk Contribution, never "Maximum
Recommended Concentration".

This module reuses the same real data source (risk_snapshot.json's
"marginalRiskContribution" field, Phase 3 E1) and the same projection
technique (rebalancer.py's compute_risk_budget_check(), Phase 3 E2:
scale a ticker's existing MRC by its proposed weight-ratio change) but
does NOT call into or modify rebalancer.py or risk_engine.py — their
real signatures are batch-shaped (routed_orders/bands from a full
rebalance-plan run) and not directly reusable for a single ad-hoc order
without a larger refactor of already-shipped, already-reviewed code
(out of scope here). This function independently applies the identical
formula against the identical real data source instead.

Only the traded ticker is evaluated — no cascade check across all
holdings, matching E2's own real per-ticker scope.

Layer: Backend / Python Services / Risk

Usage:
    from order_risk_gates import check_mrc_limit
    result = check_mrc_limit(order, portfolio_state, risk_snapshot=snapshot)

Key Input Dependencies:
    - investment_screener/backend/data/risk_snapshot.json (Phase 3 E1's
      "marginalRiskContribution" field)
    - investment_screener/backend/data/account_policy.json (informational —
      real "maxMarginalRiskContributionPct" default mirrored here as
      mrc_cap_pct's own default)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

RISK_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "risk_snapshot.json"
ACCOUNT_POLICY_PATH = Path(__file__).resolve().parents[1] / "data" / "account_policy.json"


def _load_risk_snapshot() -> Dict[str, Any]:
    """Load the real risk_snapshot.json, never raising.

    Returns:
        Parsed dict, or {} if the file is missing, unreadable, or
        malformed JSON — matches this project's established
        "read optional data file" pattern (e.g. load_standing_decisions()
        in brief_recommendations.py).
    """
    if not RISK_SNAPSHOT_PATH.exists():
        return {}
    try:
        with open(RISK_SNAPSHOT_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _project_new_weight(
    order: Dict[str, Any], current_weight: float, total_value: float,
) -> float:
    """Project the traded ticker's post-order portfolio weight.

    Args:
        order: {"ticker", "side", "shares", "price"}.
        current_weight: Current weight as a fraction (e.g. 0.20 for 20%).
        total_value: Current total portfolio value (assumed unchanged by
            a single order — matches E2's own first-order-estimate scope).

    Returns:
        Projected weight as a fraction, floored at 0.0 (a sell can't
        push a position below zero value in this estimate).
    """
    current_value = current_weight * total_value
    order_value = order.get("shares", 0.0) * order.get("price", 0.0)
    if order.get("side") == "BUY":
        new_value = current_value + order_value
    else:
        new_value = current_value - order_value
    return max(new_value, 0.0) / total_value


def check_mrc_limit(
    order: Dict[str, Any],
    portfolio_state: Dict[str, Any],
    risk_snapshot: Optional[Dict[str, Any]] = None,
    mrc_cap_pct: float = 25.0,
) -> Dict[str, Any]:
    """Check whether a single, ad-hoc order pushes MRC over the risk budget cap.

    Reuses the same real data source (risk_snapshot.json's
    "marginalRiskContribution" field, Phase 3 E1) and the same
    projection technique (rebalancer.py's compute_risk_budget_check(),
    Phase 3 E2: scale existing MRC by the ticker's proposed weight-ratio
    change) — this function does not recompute MRC from scratch, and
    does not call into or modify rebalancer.py/risk_engine.py (their
    real signatures are batch-shaped, not directly reusable for a
    single order without a larger refactor of already-shipped code,
    out of scope here).

    Only evaluates the traded ticker, not a "cascade" across all
    holdings — a single order changes only that ticker's own weight in
    this projection model, matching E2's own real per-ticker scope.

    Never raises: a missing/unreadable risk_snapshot, a ticker with no
    prior MRC data (e.g. a brand-new position), or zero current weight
    all degrade to passed=True with no flag for that ticker — matches
    E2's own "skip projection rather than divide by zero or guess"
    precedent exactly.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", "shares": float,
            "price": float}.
        portfolio_state: {"holdings": {ticker: {"weight_pct": float}},
            "total_value": float} — current state BEFORE this order.
            weight_pct is a percentage (e.g. 18.0 for 18%).
        risk_snapshot: Parsed risk_snapshot.json. If None, loaded from
            the real RISK_SNAPSHOT_PATH — pass explicitly in tests to
            avoid real file I/O.
        mrc_cap_pct: The real cap (default 25.0, matching
            account_policy.json's real "maxMarginalRiskContributionPct"
            default).

    Returns:
        {
            "passed": bool,
            "holdings_flagged": [{"ticker": str, "current_mrc_pct": float,
                                   "projected_mrc_pct": float, "cap_pct": float}],
            "reason": str,
        }
        holdings_flagged is empty and passed is True if the projection
        couldn't be computed (missing data) OR if the projected MRC
        stays within cap.
    """
    if risk_snapshot is None:
        risk_snapshot = _load_risk_snapshot()

    mrc_map = (risk_snapshot or {}).get("marginalRiskContribution", {})
    ticker = order.get("ticker")
    old_mrc = mrc_map.get(ticker)  # a fraction, e.g. 0.18 for 18%

    holdings = portfolio_state.get("holdings", {})
    total_value = portfolio_state.get("total_value", 0.0)
    current_weight_pct = holdings.get(ticker, {}).get("weight_pct", 0.0)
    current_weight = current_weight_pct / 100.0

    if old_mrc is None or current_weight <= 0 or total_value <= 0:
        return {
            "passed": True,
            "holdings_flagged": [],
            "reason": "MRC projection unavailable (no prior data or zero weight) — order not blocked",
        }

    new_weight = _project_new_weight(order, current_weight, total_value)
    projected_mrc_pct = old_mrc * 100 * (new_weight / current_weight)

    if projected_mrc_pct > mrc_cap_pct:
        flagged = [{
            "ticker": ticker,
            "current_mrc_pct": old_mrc * 100,
            "projected_mrc_pct": projected_mrc_pct,
            "cap_pct": mrc_cap_pct,
        }]
        return {
            "passed": False,
            "holdings_flagged": flagged,
            "reason": f"Estimated MRC would reach {projected_mrc_pct:.1f}% (estimate) > {mrc_cap_pct}% cap",
        }

    return {"passed": True, "holdings_flagged": [], "reason": "Within MRC budget"}
