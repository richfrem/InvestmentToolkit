"""
Order Risk Gates — MRC Risk Gate (Task 5E-1) + Cluster Variance Gate (Task
5E-2) + Thesis Breaker Veto (Task 5E-3)

check_mrc_limit() (5E-1) checks whether a single, ad-hoc order would push
its ticker's real Marginal Risk Contribution (MRC) — Phase 3 E1's
correlation/covariance-aware risk-decomposition metric from
risk_engine.py's compute_marginal_risk_contribution() — over the
portfolio's real risk budget cap. "MRC" here is Marginal Risk
Contribution, never "Maximum Recommended Concentration".

check_cluster_variance() (5E-2) checks whether a single, ad-hoc BUY
order's pillar (sub-strategy cluster) already has variance contribution
— Phase 3 E1's compute_cluster_exposure() output — over the real risk
budget cap. Unlike check_mrc_limit(), this is NOT a post-order
projection: it mirrors rebalancer.py's compute_risk_budget_check() (E2)
exactly, which only checks the pillar's CURRENT variance contribution,
never a simulated post-trade increase.

check_breaker_veto() (5E-3) checks whether a single, ad-hoc BUY order's
ticker has a TRIGGERED thesis breaker (Phase 3 B5) and vetoes if so. It
reads the REAL data/thesis_breaker_state.json (machine-owned by
thesis_breakers.py) — NEVER target-portfolio.json, which only stores
human-authored breaker DEFINITIONS, never live triggered/OK status.
Unlike rebalancer.py's compute_breaker_warnings() (Phase 3 E2, warn-only,
never vetoes, batch-shaped), this function returns a REAL veto for a
single ad-hoc order — Task 5E's own veto authority.

This module reuses the same real data sources (risk_snapshot.json's
"marginalRiskContribution" and "clusterExposure" fields, Phase 3 E1;
thesis_breaker_state.json's "holdings" map, Phase 3 B5) and the same
real check logic from rebalancer.py's compute_risk_budget_check() and
compute_breaker_warnings() (Phase 3 E2) but does NOT call into or
modify rebalancer.py, risk_engine.py, or thesis_breakers.py — their
real signatures are batch-shaped (routed_orders/bands from a full
rebalance-plan run) and not directly reusable for a single ad-hoc order
without a larger refactor of already-shipped, already-reviewed code
(out of scope here). These functions independently apply the identical
logic against the identical real data sources instead.

Only the traded ticker (and its pillar) is evaluated — no cascade check
across all holdings, matching E2's own real per-ticker scope.

check_order_size() (Task 5E-4) checks whether a single, ad-hoc order's
share count exceeds a safe percentage of the ticker's average daily
trading volume — a liquidity/market-impact safeguard, distinct from
Task 5D-8's compute_liquidity_score() (which only has a single TV
candle's Volume + intraday range available as a rough live-chart
proxy). This gate reuses market_data.py's real, cached get_prices()
(Phase 1's yfinance data layer) via get_average_daily_volume() instead
of calling yfinance directly a second time.

Layer: Backend / Python Services / Risk

Usage:
    from order_risk_gates import check_mrc_limit, check_cluster_variance, check_breaker_veto, check_order_size
    result = check_mrc_limit(order, portfolio_state, risk_snapshot=snapshot)
    result = check_cluster_variance(order, portfolio_state, risk_snapshot=snapshot)
    result = check_breaker_veto(order, thesis_breaker_state=state)
    result = check_order_size(order, daily_volume=avg_volume)

Key Input Dependencies:
    - investment_screener/backend/data/risk_snapshot.json (Phase 3 E1's
      "marginalRiskContribution" and "clusterExposure" fields)
    - investment_screener/backend/data/account_policy.json (informational —
      real "maxMarginalRiskContributionPct" and
      "maxClusterVarianceContributionPct" defaults mirrored here as
      mrc_cap_pct's / cluster_cap_pct's own defaults)
    - investment_screener/backend/data/thesis_breaker_state.json (Phase 3
      B5's real live triggered/OK breaker status, machine-owned by
      thesis_breakers.py — never target-portfolio.json)
    - market_data.py's get_prices() (Phase 1's real, cached yfinance OHLCV
      data layer, same directory — reused by get_average_daily_volume(),
      never re-fetched via yfinance directly)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

RISK_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "risk_snapshot.json"
ACCOUNT_POLICY_PATH = Path(__file__).resolve().parents[1] / "data" / "account_policy.json"
THESIS_BREAKER_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "thesis_breaker_state.json"


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


def check_cluster_variance(
    order: Dict[str, Any],
    portfolio_state: Dict[str, Any],
    risk_snapshot: Optional[Dict[str, Any]] = None,
    cluster_cap_pct: float = 60.0,
) -> Dict[str, Any]:
    """Check whether a BUY order's pillar (sub-strategy cluster) already
    has variance contribution over the real risk budget cap.

    Reuses the SAME real data source as rebalancer.py's
    compute_risk_budget_check() (Phase 3 E2): risk_snapshot.json's
    "clusterExposure" list (Phase 3 E1's compute_cluster_exposure()
    output — real, already-computed per-pillar variance contribution),
    checked against the real "maxClusterVarianceContributionPct" cap
    (default 60.0).

    NOT a post-order projection — matches E2's own real behavior
    exactly: this checks whether the pillar's CURRENT variance
    contribution already exceeds cap, for ANY buy in that pillar,
    regardless of order size. E2 itself does not simulate a post-trade
    cluster-variance increase (unlike MRC's weight-ratio scaling,
    Task 5E-1) — this function does not invent one either.

    SELL orders are never flagged — reducing a position cannot push a
    pillar's variance contribution up, matching E2's own real scope
    (E2 only evaluates "buy" actions for this check).

    Never raises: missing risk_snapshot, a ticker with no pillar
    assignment (falls back to "unassigned", same as E1's own
    pillar_map.get(ticker, "unassigned") convention), or a pillar with
    no clusterExposure entry all degrade to passed=True.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", "shares": float,
            "price": float}.
        portfolio_state: {"holdings": {ticker: {"pillar_id": str}}, ...}
            — must include each holding's pillar assignment. Uses
            snake_case "pillar_id" here (matching this module's own
            portfolio_state dict convention, e.g. 5E-1's "weight_pct"),
            distinct from the real underlying source file's camelCase
            "pillarId" (target-portfolio.json) — this is an ad-hoc
            caller-constructed dict, not raw target-portfolio.json.
        risk_snapshot: Parsed risk_snapshot.json. If None, loaded via
            the same _load_risk_snapshot() helper Task 5E-1 already
            defined (reused, not duplicated).
        cluster_cap_pct: Real cap (default 60.0, matching
            account_policy.json's real "maxClusterVarianceContributionPct").

    Returns:
        {"passed": bool, "pillar": str | None, "variance_pct": float | None, "reason": str}
    """
    if order.get("side") != "BUY":
        return {"passed": True, "pillar": None, "variance_pct": None, "reason": "Not a buy order — cluster variance gate only applies to buys"}

    if risk_snapshot is None:
        risk_snapshot = _load_risk_snapshot()

    ticker = order.get("ticker")
    holdings = portfolio_state.get("holdings", {})
    pillar = holdings.get(ticker, {}).get("pillar_id", "unassigned")

    cluster_list = (risk_snapshot or {}).get("clusterExposure", [])
    cluster_map = {c.get("pillarId"): c for c in cluster_list if isinstance(c, dict)}
    cluster_entry = cluster_map.get(pillar)

    if cluster_entry is None:
        return {"passed": True, "pillar": pillar, "variance_pct": None, "reason": "No cluster data for this pillar — order not blocked"}

    variance_pct = cluster_entry.get("varianceContributionPct", 0.0)
    if variance_pct > cluster_cap_pct:
        return {
            "passed": False,
            "pillar": pillar,
            "variance_pct": variance_pct,
            "reason": f"Pillar '{pillar}' cluster variance already {variance_pct:.1f}% > {cluster_cap_pct}% cap",
        }

    return {"passed": True, "pillar": pillar, "variance_pct": variance_pct, "reason": "Within cluster variance budget"}


def _load_thesis_breaker_state() -> Dict[str, Any]:
    """Load the real data/thesis_breaker_state.json, never raising.

    Mirrors _load_risk_snapshot()'s (Task 5E-1) exact pattern for a
    different real data file — machine-owned by thesis_breakers.py
    (Phase 3 B5).

    Returns:
        Parsed dict, or {} if the file is missing, unreadable, or
        malformed JSON.
    """
    try:
        if not THESIS_BREAKER_STATE_PATH.exists():
            return {}
        return json.loads(THESIS_BREAKER_STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def check_breaker_veto(
    order: Dict[str, Any],
    thesis_breaker_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Check whether a BUY order's ticker has a TRIGGERED thesis breaker
    (Phase 3 B5) and veto if so.

    Reads the real data/thesis_breaker_state.json (machine-owned by
    thesis_breakers.py, B5) — NOT target-portfolio.json, which only
    stores breaker DEFINITIONS, never live triggered/OK status. A
    breaker is TRIGGERED iff its "status" field is the literal string
    "TRIGGERED", matching rebalancer.py's real
    compute_breaker_warnings() check exactly.

    Unlike E2's compute_breaker_warnings() (warn-only, never vetoes,
    batch-shaped), this function returns a REAL veto for a single
    ad-hoc order — Task 5E's own veto authority, analogous to how G2's
    risk_officer.py already turns E2's warnings into a real veto for
    the batch rebalance-plan workflow.

    SELL orders are never vetoed — matches E2's own real "buy actions
    only" scope for the equivalent check.

    Never raises: missing state file, a ticker with no breaker entries,
    or no TRIGGERED breaker for this ticker all degrade to passed=True.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", ...}.
        thesis_breaker_state: Parsed thesis_breaker_state.json. If
            None, loaded via _load_thesis_breaker_state().

    Returns:
        {"passed": bool, "breaker": str | None, "reason": str} —
        "breaker" is the FIRST TRIGGERED breaker_id found for this
        ticker (a ticker could theoretically have multiple triggered
        breakers; only the first is surfaced, matching the plan's own
        singular "breaker: str or None" return contract, not a list).
    """
    if order.get("side") != "BUY":
        return {"passed": True, "breaker": None, "reason": "Not a buy order — breaker veto only applies to buys"}

    if thesis_breaker_state is None:
        thesis_breaker_state = _load_thesis_breaker_state()

    ticker = order.get("ticker")
    breakers = (thesis_breaker_state or {}).get("holdings", {}).get(ticker, {})

    for breaker_id, entry in breakers.items():
        if isinstance(entry, dict) and entry.get("status") == "TRIGGERED":
            return {
                "passed": False,
                "breaker": breaker_id,
                "reason": f"TRIGGERED breaker '{breaker_id}' for {ticker} (current value {entry.get('currentValue')!r})",
            }

    return {"passed": True, "breaker": None, "reason": "No triggered breaker for this ticker"}


def get_average_daily_volume(ticker: str, days: int = 10) -> Optional[int]:
    """
    Fetch a ticker's average daily volume over the last `days` trading
    days, reusing market_data.py's real, cached get_prices() (Phase 1)
    — does NOT call yfinance directly a second time.

    Never raises: any fetch failure, exception, or empty result
    degrades to None.

    Args:
        ticker: Ticker symbol.
        days: Number of trailing trading days to average over (default 10).

    Returns:
        Average daily volume (int, rounded), or None if unavailable.
    """
    from market_data import get_prices
    try:
        result = get_prices([ticker], period=f"{days}d", interval="1d")
    except Exception:
        return None

    rows = result.get(ticker, {}).get("data", [])
    volumes = [r["volume"] for r in rows if isinstance(r, dict) and "volume" in r]
    if not volumes:
        return None
    return int(sum(volumes) / len(volumes))


def check_order_size(
    order: Dict[str, Any],
    daily_volume: Optional[float] = None,
    max_pct_of_volume: float = 10.0,
) -> Dict[str, Any]:
    """
    Check whether an order's share count exceeds a safe percentage of
    the ticker's average daily trading volume — a liquidity/market-
    impact safeguard.

    Distinct from Task 5D-8's compute_liquidity_score() (which uses a
    single TV candle's Volume + intraday range as a rough proxy for a
    live chart read) — this gate uses REAL multi-day average daily
    volume fetched via market_data.py's get_prices() (Phase 1's real,
    cached yfinance data layer), a more reliable signal for a genuine
    pre-trade size check.

    If daily_volume isn't supplied, fetches it via
    get_average_daily_volume() — pass it explicitly in tests to avoid
    real network/yfinance calls.

    Never raises: a missing/unfetchable daily_volume degrades to
    passed=True (can't evaluate, don't block an order on missing data
    — matches every other gate in this module's consistent posture).

    Boundary convention matches 5E-1/5E-2's established pattern (fail
    strictly ABOVE the cap, not at-or-above): an order at EXACTLY
    max_pct_of_volume passes.

    Args:
        order: {"ticker": str, "shares": float, ...}.
        daily_volume: Average daily volume for the ticker, or None to
            fetch it via get_average_daily_volume().
        max_pct_of_volume: Max order size as % of daily volume (default
            10.0, per the plan's literal example).

    Returns:
        {"passed": bool, "size_pct_of_volume": float | None, "reason": str}
    """
    if daily_volume is None:
        daily_volume = get_average_daily_volume(order.get("ticker"))

    if not daily_volume or daily_volume <= 0:
        return {"passed": True, "size_pct_of_volume": None, "reason": "Daily volume unavailable — order not blocked"}

    shares = order.get("shares", 0.0)
    size_pct = (shares / daily_volume) * 100

    if size_pct > max_pct_of_volume:
        return {
            "passed": False,
            "size_pct_of_volume": size_pct,
            "reason": f"Order size {size_pct:.1f}% of daily volume > {max_pct_of_volume}% cap",
        }

    return {"passed": True, "size_pct_of_volume": size_pct, "reason": "Within size limit"}
