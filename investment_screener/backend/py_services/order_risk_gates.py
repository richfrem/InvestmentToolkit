"""
Order Risk Gates — MRC Risk Gate (Task 5E-1) + Cluster Variance Gate (Task
5E-2) + Thesis Breaker Veto (Task 5E-3) + Order Size Gate (Task 5E-4) +
Balance Gate (Task 5E-5) + Post-Trade Validation (Task 5E-7) + Data
Readiness Gate (5E-fix, closing the previously-orphaned Task 5D-8
integration) + real place_order.py wiring (5E-fix)

build_portfolio_state_for_order() constructs the real portfolio_state dict
check_mrc_limit()/check_cluster_variance() require, from the REAL
target-portfolio.json + portfolio.json data files — reusing risk_engine.py's
compute_risk_snapshot() pillar_map pattern and portfolio_io.py's
load_portfolio_state()/compute_weights() unchanged. This is the real
integration point place_order.py (the CLI's actual order-placement
entrypoint) now uses instead of every caller hand-building portfolio_state.

check_data_readiness_gate() (5E-fix) is the missing caller
data_window_validator.py's check_order_data_readiness() (Task 5D-8) was
built for — that function's own docstring says it's "designed to be
imported and called FROM [order_risk_gates.py] once it exists." It vetoes a
BUY order ONLY on a live RSI-overbought read; liquidity_score is always
surfaced but never gates on its own. This is check_risk_gates()'s 6th gate.

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

check_available_balance() (Task 5E-5) checks whether enough cash is
available to cover a single, ad-hoc BUY order's cost. Reuses the real,
already-synced data/portfolio.json broker snapshot (this project's
existing, established multi-fallback TradingView/Questrade sync
pipeline, CLAUDE.md pitfall #20) via get_available_cash() instead of
implementing a new live Questrade API integration from scratch — the
plan's own checklist explicitly allows "(or cached snapshot)" as an
alternative. Reads either the portfolio-wide totals.cashUSD or a
specific account's tvSnapshot.snapshots[].balances.cashUSD (matched by
accountType). Read-only — never writes to portfolio.json, which is
gitignored, sacred user data per this project's own CLAUDE.md rule.

get_trade_log_entries() / find_matching_trade_log_entry() /
wait_for_trade_log_entry() / validate_trade_execution() (Task 5E-7)
reconcile a placed order against the real trade log (investment_screener/
backend/data/trade-log.json — this project's existing manual/CDP-synced
trade log, written by trading.ts's makeLogEntry(), NOT a new store).
get_trade_log_entries() reads it; find_matching_trade_log_entry() finds
the newest entry matching an order's ticker/side/(account) that is in a
real executed state — entries with status in {"suggested", "cancelled",
"inactive", "submitted"} are excluded, since this project's real schema
has no "filled"/"executed" status and a cancelled, price=0 CDP-logged
entry would otherwise silently corrupt a slippage calculation (a real,
observed shape in the live trade log, not a defensive guess).
wait_for_trade_log_entry() polls the two above until a match appears or
a timeout elapses, since an order placed via CDP is logged
asynchronously. validate_trade_execution() is a pure comparison (no I/O)
between an order and its already-matched trade log entry: shares must
reconcile exactly (a float-epsilon check, not a percentage tolerance),
while price slippage is flagged only above a percentage cap (default
2.0%, exclusive — matches this module's `>` not `>=` boundary
convention elsewhere). Never raises — a zero/missing order price skips
the slippage calculation entirely rather than raising or reporting
100%/undefined slippage.

Layer: Backend / Python Services / Risk

Usage:
    from order_risk_gates import check_mrc_limit, check_cluster_variance, check_breaker_veto, check_order_size, check_available_balance, check_data_readiness_gate
    result = check_mrc_limit(order, portfolio_state, risk_snapshot=snapshot)
    result = check_cluster_variance(order, portfolio_state, risk_snapshot=snapshot)
    result = check_breaker_veto(order, thesis_breaker_state=state)
    result = check_order_size(order, daily_volume=avg_volume)
    result = check_available_balance(order, questrade_cash=cash)
    result = check_data_readiness_gate(order, data_readiness=readiness)

    from order_risk_gates import build_portfolio_state_for_order, check_risk_gates
    portfolio_state = build_portfolio_state_for_order()
    result = check_risk_gates(order, portfolio_state)  # composes all 6 gates

    from order_risk_gates import wait_for_trade_log_entry, validate_trade_execution
    matched_entry = wait_for_trade_log_entry(order, account="TFSA")
    result = validate_trade_execution(order, matched_entry)

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
    - investment_screener/backend/data/target-portfolio.json (pillarId per
      ticker, used by build_portfolio_state_for_order() — same file
      risk_engine.py's compute_risk_snapshot() reads for its own pillar_map)
    - market_data.py's get_prices() (Phase 1's real, cached yfinance OHLCV
      data layer, same directory — reused by get_average_daily_volume(),
      never re-fetched via yfinance directly)
    - investment_screener/backend/data/portfolio.json (gitignored, the
      real, already-synced broker snapshot — "totals.cashUSD" and
      "tvSnapshot.snapshots[].balances.cashUSD", never written to; also
      read via portfolio_io.load_portfolio_state()/compute_weights() by
      build_portfolio_state_for_order() for real actual weights)
    - data_window_validator.py's check_order_data_readiness() (Task 5D-8,
      same directory — a LIVE TradingView CDP Data Window read, lazily
      imported inside check_data_readiness_gate() to avoid triggering it
      at module-import time)
    - investment_screener/backend/data/trade-log.json (gitignored, the
      real manual/CDP-synced trade log, written by trading.ts's
      makeLogEntry() — "TRADE_LOG_FILE" in paths.ts — never written to
      by this module, only read)
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Sibling module in the same py_services/ directory — a plain top-level
# import works with no sys.path manipulation, since anything that can import
# order_risk_gates.py already has this directory on sys.path (matches this
# codebase's established same-directory import convention, e.g. how
# risk_engine.py itself reuses portfolio_io.load_portfolio_state()/
# compute_weights() for its own compute_risk_snapshot()).
from portfolio_io import compute_weights, load_portfolio_state

RISK_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "risk_snapshot.json"
ACCOUNT_POLICY_PATH = Path(__file__).resolve().parents[1] / "data" / "account_policy.json"
THESIS_BREAKER_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "thesis_breaker_state.json"
TARGET_PORTFOLIO_PATH = Path(__file__).resolve().parents[1] / "data" / "theses" / "target-portfolio.json"
PORTFOLIO_PATH = Path(__file__).resolve().parents[1] / "data" / "portfolio.json"
TRADE_LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "trade-log.json"
ORDERS_EXECUTED_PATH = Path(__file__).resolve().parents[1] / "data" / "orders_executed.jsonl"


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


def build_portfolio_state_for_order(
    target_portfolio_path: Optional[Path] = None,
    portfolio_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build the real portfolio_state dict check_mrc_limit()/
    check_cluster_variance() require, from the REAL data files — this is the
    missing "real caller convenience" these gates never had until now (every
    existing test constructs portfolio_state by hand).

    Reuses the EXACT same pattern already established in risk_engine.py's
    compute_risk_snapshot(): loads target-portfolio.json to build a
    ticker -> pillarId map, loads portfolio.json via portfolio_io's
    load_portfolio_state()/compute_weights() for actual weights — no weight
    math is reimplemented here, both real, already-reviewed functions are
    reused unchanged.

    Never raises: a missing/unreadable/malformed target-portfolio.json OR
    portfolio.json (or a portfolio_io failure of any kind) degrades to
    {"holdings": {}, "total_value": 0.0} — matches how every gate that
    consumes portfolio_state already treats a zero/missing weight or
    total_value (check_mrc_limit/check_cluster_variance both degrade to
    passed=True in that case), so this degradation is a safe, intentional
    "can't evaluate, don't block" fallback, not a new failure mode.

    Args:
        target_portfolio_path: Override path (tests use tmp_path); None reads
            the real TARGET_PORTFOLIO_PATH.
        portfolio_path: Override path (tests use tmp_path); None reads the
            real PORTFOLIO_PATH.

    Returns:
        {"holdings": {ticker: {"weight_pct": float, "pillar_id": str}},
        "total_value": float} — the union of every ticker with a pillar
        assignment AND every ticker with an actual portfolio weight (a
        ticker held but not yet pillar-assigned gets "unassigned"; a
        pillar-assigned ticker not currently held gets weight_pct=0.0 rather
        than being omitted).
    """
    target_path = target_portfolio_path or TARGET_PORTFOLIO_PATH
    try:
        target_data = json.loads(Path(target_path).read_text())
    except (OSError, json.JSONDecodeError):
        return {"holdings": {}, "total_value": 0.0}

    pillar_map = {
        h["ticker"]: h.get("pillarId", "unassigned")
        for h in target_data.get("holdings", [])
    }

    try:
        state = load_portfolio_state(Path(portfolio_path or PORTFOLIO_PATH))
    except (OSError, json.JSONDecodeError):
        return {"holdings": {}, "total_value": 0.0}

    weights_pct = compute_weights(state["shares"], state["prices"], state["total_usd"])

    holdings = {
        ticker: {
            "weight_pct": weights_pct.get(ticker, 0.0),
            "pillar_id": pillar_map.get(ticker, "unassigned"),
        }
        for ticker in set(pillar_map) | set(weights_pct)
    }

    return {"holdings": holdings, "total_value": state["total_usd"]}


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
    pre-trade size check. 5D-8's own signal (RSI overbought veto +
    liquidity score) is NOW independently consumed via
    check_data_readiness_gate() (the 6th gate in check_risk_gates()'s
    composition) — this function's ADV-based check remains a
    deliberately separate, complementary signal, not a duplicate: they
    answer different questions (multi-day real trading volume vs. a
    single live candle's liquidity+momentum snapshot).

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


def get_available_cash(account: Optional[str] = None) -> Optional[float]:
    """
    Fetch available USD cash from the real, synced portfolio.json
    snapshot (this project's existing, established multi-fallback
    broker sync — not a live Questrade API call implemented from
    scratch here).

    Args:
        account: Specific account type (e.g. "TFSA", "RRSP") to read
            that account's own cashUSD from tvSnapshot.snapshots[]
            (matched by accountType), or None for the portfolio-wide
            totals.cashUSD.

    Never raises: missing file, malformed JSON, or no matching account
    all degrade to None.

    Returns:
        Available USD cash, or None if unavailable.
    """
    try:
        if not PORTFOLIO_PATH.exists():
            return None
        data = json.loads(PORTFOLIO_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    if account is None:
        return data.get("totals", {}).get("cashUSD")

    for snapshot in data.get("tvSnapshot", {}).get("snapshots", []):
        if snapshot.get("accountType") == account:
            return snapshot.get("balances", {}).get("cashUSD")
    return None


def check_available_balance(
    order: Dict[str, Any],
    questrade_cash: Optional[float] = None,
    account: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check whether enough cash is available to cover a BUY order's cost.

    If questrade_cash isn't supplied, fetches it via
    get_available_cash(account) — pass it explicitly in tests to avoid
    real file I/O.

    SELL orders are never evaluated — selling doesn't require cash,
    matching this module's established pattern (5E-2/5E-3) of only
    gating BUY-side actions where the check is directionally
    meaningful.

    Missing cash data degrades to passed=True — matches every other
    gate in this module's consistent "can't evaluate, don't block real
    trading on an estimate/data gap" posture (5E-1 through 5E-4 all do
    the same). This gate does not introduce a different, inconsistent
    failure policy just because a cash shortfall has a more immediate
    real-world consequence than an MRC/cluster/size estimate — the
    actual broker will still reject an order it can't afford
    regardless of what this advisory gate reports.

    Never raises.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", "shares": float,
            "price": float}.
        questrade_cash: Available cash, or None to fetch via
            get_available_cash().
        account: Passed through to get_available_cash() if
            questrade_cash isn't supplied — which account's cash to
            check (None = portfolio-wide total).

    Returns:
        {"passed": bool, "cash_required": float, "cash_available": float | None, "reason": str}
    """
    if order.get("side") != "BUY":
        return {"passed": True, "cash_required": 0.0, "cash_available": questrade_cash, "reason": "Not a buy order — balance gate only applies to buys"}

    if questrade_cash is None:
        questrade_cash = get_available_cash(account)

    cash_required = order.get("shares", 0.0) * order.get("price", 0.0)

    if questrade_cash is None:
        return {"passed": True, "cash_required": cash_required, "cash_available": None, "reason": "Available cash unknown — order not blocked"}

    if questrade_cash < cash_required:
        return {
            "passed": False,
            "cash_required": cash_required,
            "cash_available": questrade_cash,
            "reason": f"Insufficient cash: ${questrade_cash:,.2f} available, ${cash_required:,.2f} required",
        }

    return {"passed": True, "cash_required": cash_required, "cash_available": questrade_cash, "reason": "Sufficient cash"}


# --- Task 5E-fix: Data Readiness Gate (closes the 5D-8 -> 5E integration) ---
#
# check_data_readiness_gate() is the missing caller data_window_validator.py's
# check_order_data_readiness() (Task 5D-8) was built for — that function's own
# docstring says it's "designed to be imported and called FROM
# [order_risk_gates.py] once it exists." This gate closes that gap.


def check_data_readiness_gate(
    order: Dict[str, Any],
    data_readiness: Optional[Dict[str, Any]] = None,
    rsi_veto_threshold: float = 80.0,
) -> Dict[str, Any]:
    """Check a BUY order against Task 5D-8's live TV Data Window read —
    vetoes ONLY on an RSI-overbought condition; a low liquidity score is
    informational only.

    Closes the previously-orphaned 5D-8 -> 5E integration:
    data_window_validator.py's check_order_data_readiness() was fully
    built and unit-tested (Task 5D-8) but had zero production callers —
    its own docstring literally says it's "designed to be imported and
    called FROM [order_risk_gates.py] once it exists." This is that
    caller.

    BUY-only, matching this module's established convention for
    directionally-meaningful checks (5E-2/5E-3/5E-5 are all buy-only) —
    an RSI-overbought/liquidity read has no meaningful veto interpretation
    for a SELL.

    Only "rsi_veto" actually gates (fails) the order. "liquidity_score" is
    ALWAYS surfaced in the return dict regardless of pass/fail — per
    5D-8's own docstring distinction between "reports data" (liquidity)
    and "gates" (RSI veto only): a low liquidity score does not, by
    itself, fail this gate (that would be a new, undocumented gating
    policy this task does not introduce).

    If data_readiness isn't supplied, this function lazily imports and
    calls data_window_validator.check_order_data_readiness() INSIDE this
    function body (not at module level) — matching this module's own
    existing convention for expensive, side-effecting fetches (e.g.
    get_average_daily_volume()'s own function-local `from market_data
    import get_prices`). The lazy import matters more here than
    anywhere else in this module: this one call triggers a LIVE
    TradingView CDP chart-switch, something this module should never do
    merely by being imported.

    Never raises: check_order_data_readiness() (5D-8) itself already
    never raises by its own contract, but this function wraps the call
    in an extra try/except Exception anyway, as defense-in-depth
    specifically for this gate. Every other gate in this module only
    reads local files (already trivially safe to leave uncaught per
    Task 5D-7's own "don't defensively wrap an already-never-raising
    call" precedent, reused by check_risk_gates() itself) — this is the
    ONE gate that reaches out to a live external system (TV CDP) via a
    chain of several composed functions, so a slightly more defensive
    posture is justified here specifically, not a blanket change to
    this module's philosophy.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", ...}.
        data_readiness: check_order_data_readiness()'s own output shape
            ({"rsi_veto": {"vetoed": bool, "reason": str|None, "rsi":
            float|None}, "liquidity": {"score": float, ...}, ...}). If
            None, fetched live via check_order_data_readiness(ticker,
            rsi_veto_threshold=rsi_veto_threshold) — pass explicitly in
            tests to avoid a real TV CDP call.
        rsi_veto_threshold: Forwarded to check_order_data_readiness() when
            data_readiness isn't supplied (default 80.0, matching 5D-8's
            own default).

    Returns:
        {"passed": bool, "rsi": float | None, "liquidity_score": float | None,
        "reason": str}.
    """
    if order.get("side") != "BUY":
        return {
            "passed": True,
            "rsi": None,
            "liquidity_score": None,
            "reason": "Not a buy order — data readiness gate only applies to buys",
        }

    if data_readiness is None:
        try:
            from data_window_validator import check_order_data_readiness
            data_readiness = check_order_data_readiness(
                order.get("ticker"), rsi_veto_threshold=rsi_veto_threshold
            )
        except Exception:
            return {
                "passed": True,
                "rsi": None,
                "liquidity_score": None,
                "reason": "Data readiness check unavailable — order not blocked",
            }

    rsi_veto = (data_readiness or {}).get("rsi_veto") or {}
    liquidity_score = ((data_readiness or {}).get("liquidity") or {}).get("score")
    rsi = rsi_veto.get("rsi")

    if rsi_veto.get("vetoed"):
        return {
            "passed": False,
            "rsi": rsi,
            "liquidity_score": liquidity_score,
            "reason": f"Data readiness veto: {rsi_veto.get('reason')}",
        }

    return {
        "passed": True,
        "rsi": rsi,
        "liquidity_score": liquidity_score,
        "reason": "No RSI-overbought veto",
    }


# --- Task 5E-6: Composite Gate Check ---
#
# check_risk_gates() is the natural composition point for all six gates:
# it calls check_mrc_limit(), check_cluster_variance(), check_breaker_veto(),
# check_order_size(), check_available_balance() (Tasks 5E-1 through 5E-5),
# and check_data_readiness_gate() (the 5E-fix task above, closing the 5D-8
# integration) unchanged — pure composition, no new gate logic of its own.
# See this task's brief for the full design rationale.


def check_risk_gates(
    order: Dict[str, Any],
    portfolio_state: Dict[str, Any],
    risk_snapshot: Optional[Dict[str, Any]] = None,
    thesis_breaker_state: Optional[Dict[str, Any]] = None,
    daily_volume: Optional[float] = None,
    questrade_cash: Optional[float] = None,
    data_readiness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run all 6 order risk gates against a single order and aggregate
    results: Tasks 5E-1 through 5E-5 (mrc, cluster_variance, breaker_veto,
    size, balance) plus the 5E-fix data_readiness gate that closes Task
    5D-8's previously-orphaned integration.

    Composes check_mrc_limit(), check_cluster_variance(),
    check_breaker_veto(), check_order_size(), check_available_balance(),
    and check_data_readiness_gate() unchanged — no new gate logic, this
    function only orchestrates and aggregates.

    risk_snapshot and thesis_breaker_state are each loaded AT MOST ONCE
    here (if not supplied) and shared across the gates that use them
    (MRC + cluster variance both need risk_snapshot) — avoids each gate
    independently re-reading the same real file twice per
    check_risk_gates() call. daily_volume and questrade_cash are each
    only used by one gate (size, balance respectively), so no sharing
    concern applies to them.

    data_readiness is deliberately NOT eagerly fetched here, unlike
    risk_snapshot/thesis_breaker_state — this function passes
    data_readiness=None straight through to check_data_readiness_gate()
    and lets THAT function do its own lazy fetch. risk_snapshot and
    thesis_breaker_state are cheap local file reads shared by two gates
    each, so loading them once up front avoids a redundant duplicate
    file read; data_readiness is a single expensive LIVE TV CDP round-
    trip used by exactly one gate, so eager-loading it here would waste
    a live CDP call on every check_risk_gates() invocation that doesn't
    even care about data readiness (e.g. tests that supply
    daily_volume=/questrade_cash= explicitly but not data_readiness=).

    IMPORTANT — unlike the other 5 gates (pure local file reads/
    computation), this 6th gate can make a LIVE TradingView CDP call
    (chart switch + Data Window read, with 5D-1's own retry/backoff
    contract) when data_readiness isn't supplied — this can be slow
    (multiple seconds under retry). Callers needing a fast, synchronous
    result (e.g. tests, or a caller that already has a fresh
    data_readiness read from elsewhere) should pass data_readiness=
    explicitly to skip the live call entirely.

    Never raises by design: every individual gate already never raises
    (5E-1 through 5E-5's own "never raises" contracts; the new
    data_readiness gate also never raises, with its own extra
    defense-in-depth try/except around its live CDP call — see
    check_data_readiness_gate()'s docstring), so this function adds no
    new exception surface in practice. If a gate's own contract were
    ever violated and it DID raise, this function deliberately does NOT
    catch it — matching Task 5D-7's own precedent
    (get_validated_data_window(), which composes several "never raises"
    functions without adding a defensive try/except around them). A
    gate raising is treated as a genuine regression in that gate's own
    contract and is allowed to surface loudly, rather than being
    silently swallowed into a misleading passed=True/False result for
    a real trading decision.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", "shares": float, "price": float}.
        portfolio_state: Shared input for the MRC and cluster-variance
            gates (see Tasks 5E-1/5E-2's own real field requirements).
        risk_snapshot: Shared MRC/cluster data source. If None, loaded
            once via _load_risk_snapshot() (5E-1) and reused for both.
        thesis_breaker_state: See Task 5E-3. If None, loaded once via
            _load_thesis_breaker_state() (5E-3).
        daily_volume: See Task 5E-4. If None, check_order_size() fetches
            it internally via get_average_daily_volume().
        questrade_cash: See Task 5E-5. If None, check_available_balance()
            fetches it internally via get_available_cash().
        data_readiness: See check_data_readiness_gate() above. If None,
            that gate fetches it internally via a LIVE TV CDP call — pass
            it explicitly (e.g. from an already-fetched value) to avoid
            that live round-trip, exactly as this module's own tests do.

    Returns:
        {
            "passed": bool,  # True only if ALL 6 gates passed
            "gates": [{"name": str, "passed": bool, "reason": str, ...}],
                # one entry per gate, in a fixed order: mrc, cluster_variance,
                # breaker_veto, size, balance, data_readiness — each entry
                # is that gate's own full result dict with a "name" key added
            "reasons": [str],  # "reason" strings from FAILING gates only,
                # in the same fixed gate order
        }
    """
    if risk_snapshot is None:
        risk_snapshot = _load_risk_snapshot()
    if thesis_breaker_state is None:
        thesis_breaker_state = _load_thesis_breaker_state()

    mrc_result = check_mrc_limit(order, portfolio_state, risk_snapshot=risk_snapshot)
    cluster_result = check_cluster_variance(order, portfolio_state, risk_snapshot=risk_snapshot)
    breaker_result = check_breaker_veto(order, thesis_breaker_state=thesis_breaker_state)
    size_result = check_order_size(order, daily_volume=daily_volume)
    balance_result = check_available_balance(order, questrade_cash=questrade_cash)
    data_readiness_result = check_data_readiness_gate(order, data_readiness=data_readiness)

    gates = [
        {"name": "mrc", **mrc_result},
        {"name": "cluster_variance", **cluster_result},
        {"name": "breaker_veto", **breaker_result},
        {"name": "size", **size_result},
        {"name": "balance", **balance_result},
        {"name": "data_readiness", **data_readiness_result},
    ]

    return {
        "passed": all(g["passed"] for g in gates),
        "gates": gates,
        "reasons": [g["reason"] for g in gates if not g["passed"]],
    }


# --- Task 5E-7: Post-Trade Validation ---
#
# Three genuinely separate concerns, matching this module's established
# fetch/compute split (e.g. _load_risk_snapshot() vs. check_mrc_limit()):
# get_trade_log_entries() fetches, find_matching_trade_log_entry() finds
# a match among fetched entries, wait_for_trade_log_entry() polls the
# two above until a match appears or a timeout elapses, and
# validate_trade_execution() is a pure comparison with no I/O of its own.

_NON_EXECUTED_STATUSES = {"suggested", "cancelled", "inactive", "submitted"}


def get_trade_log_entries(trade_log_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read all entries from the real trade log (investment_screener/
    backend/data/trade-log.json — this project's existing manual/CDP-synced
    trade log, not a new store).

    Never raises: missing file or malformed JSON degrades to [].

    Args:
        trade_log_path: Override path (tests pass a tmp_path fixture);
            None reads the real TRADE_LOG_PATH.

    Returns:
        List of trade log entry dicts, or [] if unavailable.
    """
    path = trade_log_path or TRADE_LOG_PATH
    try:
        if not path.exists():
            return []
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def find_matching_trade_log_entry(
    order: Dict[str, Any],
    entries: List[Dict[str, Any]],
    account: Optional[str] = None,
    after_timestamp: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Find the most recent trade log entry that matches an order's
    ticker, side, and (if supplied) account — restricted to entries in a
    real executed state.

    A trade log entry's status defaults to "logged" for both manual and
    CDP-auto-logged entries (there is no "filled"/"executed" status in
    this codebase's real schema). Entries with status in
    {"suggested", "cancelled", "inactive", "submitted"} are NEVER
    executed trades and are excluded, even if they are the most recent
    match by ticker/account/side — matching one of these (e.g. a
    cancelled, price=0 CDP entry, a real shape observed in the live
    trade log) would silently misreport slippage on a trade that never
    happened.

    Never raises.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", "shares": float,
            "price": float}.
        entries: Trade log entries, e.g. from get_trade_log_entries().
        account: If supplied, only match entries for this account
            (case-insensitive vs. the entry's UPPERCASE account field).
        after_timestamp: If supplied (ISO 8601 str), only match entries
            with loggedAt > after_timestamp — avoids matching a stale
            prior trade for the same ticker.

    Returns:
        The newest matching entry (by loggedAt), or None.
    """
    ticker = str(order.get("ticker", "")).upper()
    side = str(order.get("side", "")).lower()
    candidates = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("ticker", "")).upper() != ticker:
            continue
        if str(entry.get("action", "")).lower() != side:
            continue
        if entry.get("status") in _NON_EXECUTED_STATUSES:
            continue
        if account is not None and str(entry.get("account", "")).upper() != str(account).upper():
            continue
        if after_timestamp is not None and str(entry.get("loggedAt", "")) <= after_timestamp:
            continue
        candidates.append(entry)
    if not candidates:
        return None
    return max(candidates, key=lambda e: str(e.get("loggedAt", "")))


def wait_for_trade_log_entry(
    order: Dict[str, Any],
    account: Optional[str] = None,
    after_timestamp: Optional[str] = None,
    timeout: float = 60.0,
    poll_interval: float = 2.0,
    trade_log_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Poll the real trade log until a matching entry appears or timeout
    elapses — an order placed via CDP is logged asynchronously (this
    project's real cdp_execution sync flow), so no matching entry may
    exist yet at call time.

    Never raises: any I/O failure inside get_trade_log_entries() already
    degrades to [] (no match), so this function's own failure surface is
    just "timed out, return None".

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", "shares": float, "price": float}.
        account: Forwarded to find_matching_trade_log_entry().
        after_timestamp: Forwarded to find_matching_trade_log_entry().
        timeout: Max seconds to poll (default 60, per the plan's literal value).
        poll_interval: Seconds between polls (default 2).
        trade_log_path: Forwarded to get_trade_log_entries() (tests override).

    Returns:
        The matching entry, or None if not found within timeout.
    """
    deadline = time.monotonic() + timeout
    while True:
        entries = get_trade_log_entries(trade_log_path)
        match = find_matching_trade_log_entry(order, entries, account=account, after_timestamp=after_timestamp)
        if match is not None:
            return match
        if time.monotonic() >= deadline:
            return None
        time.sleep(poll_interval)


def validate_trade_execution(
    order: Dict[str, Any],
    trade_log_entry: Optional[Dict[str, Any]],
    slippage_cap_pct: float = 2.0,
) -> Dict[str, Any]:
    """Compare an order to its matched trade log entry — pure comparison,
    no I/O. Pass the entry found by wait_for_trade_log_entry()/
    find_matching_trade_log_entry(); this function performs no lookup
    itself.

    shares_delta is trade_log_entry.shares - order.shares (fractional
    shares are valid per this project's convention — CLAUDE.md pitfall
    #21). matched requires an exact shares match (delta within a small
    float epsilon, not a percentage tolerance — a hard reconciliation
    check, distinct from the SEPARATE price-slippage tolerance which is
    scoped to price only).

    price_slippage_pct is None (not flagged) when order price is 0 or
    missing — matches this module's consistent "can't evaluate, don't
    fail on a data gap" posture (5E-1 through 5E-6 all do the same).

    Never raises.

    Args:
        order: {"ticker": str, "side": "BUY"|"SELL", "shares": float, "price": float}.
        trade_log_entry: A matched entry (see find_matching_trade_log_entry()/
            wait_for_trade_log_entry()), or None if no match was found.
        slippage_cap_pct: Max acceptable price slippage percent (default 2.0,
            per the plan's literal example).

    Returns:
        {
            "matched": bool,  # False if trade_log_entry is None, or shares don't reconcile
            "shares_delta": float | None,
            "price_slippage_pct": float | None,
            "slippage_flagged": bool,
            "reason": str,
        }
    """
    if trade_log_entry is None:
        return {
            "matched": False,
            "shares_delta": None,
            "price_slippage_pct": None,
            "slippage_flagged": False,
            "reason": "No matching trade log entry found",
        }

    order_shares = order.get("shares", 0.0)
    logged_shares = trade_log_entry.get("shares", 0.0)
    shares_delta = logged_shares - order_shares
    shares_match = abs(shares_delta) < 1e-6

    order_price = order.get("price", 0.0)
    logged_price = trade_log_entry.get("price", 0.0)
    price_slippage_pct = None
    slippage_flagged = False
    if order_price:
        price_slippage_pct = abs(logged_price - order_price) / order_price * 100
        slippage_flagged = price_slippage_pct > slippage_cap_pct

    if not shares_match:
        reason = f"Shares mismatch: ordered {order_shares}, logged {logged_shares}"
    elif slippage_flagged:
        reason = f"Price slippage {price_slippage_pct:.2f}% exceeds {slippage_cap_pct}% cap"
    else:
        reason = "Trade execution matches order"

    return {
        "matched": shares_match,
        "shares_delta": shares_delta,
        "price_slippage_pct": price_slippage_pct,
        "slippage_flagged": slippage_flagged,
        "reason": reason,
    }


# --- Task 5E-8: Order Execution Audit Trail ---
#
# LAST task in Sub-Spec 5E (8/8). One write-only logging primitive that
# completes the audit-trail chain: signal -> alert -> gate decision ->
# order -> fill -> settlement. Loosely coupled to Tasks 5E-6/5E-7 by
# argument shape only (accepts their already-computed result dicts —
# never imports or calls check_risk_gates()/validate_trade_execution()
# directly), matching this module's established composition-by-argument
# pattern.


def log_order_execution(
    order: Dict[str, Any],
    gate_result: Dict[str, Any],
    decision: str,
    trade_execution_result: Optional[Dict[str, Any]] = None,
    orders_executed_path: Optional[Path] = None,
) -> bool:
    """
    Append one audit-trail record for an order attempt to
    data/orders_executed.jsonl.

    Append-only, NON-BLOCKING: unlike Task 5C-4's save_alert_metadata()
    (which deliberately raises on write failure for a tracked
    deliverable), this function NEVER raises — a logging failure must
    never abort or interfere with a live order already in flight. Any
    OSError (disk full, permissions, missing parent) is swallowed and
    reported via the return value only.

    Write-only by design, matching Task 5A-5's TV CDP error-logging
    precedent (append-only JSONL, no paired reader function in this
    codebase) — a reader isn't requested by the plan and isn't needed by
    any other Task 5E function, so it isn't built here (YAGNI).

    Args:
        order: The order dict being logged, e.g.
            {"ticker": str, "side": "BUY"|"SELL", "shares": float, "price": float}.
        gate_result: Task 5E-6's check_risk_gates() output — the real
            gate-passage status ({"passed": bool, "gates": [...],
            "reasons": [...]}).
        decision: The final outcome after gates (and any human
            override), e.g. "EXECUTED", "BLOCKED", "OVERRIDDEN". Caller
            supplies this — this function does not itself decide.
        trade_execution_result: Optional Task 5E-7
            validate_trade_execution() output, if post-trade
            reconciliation has already completed by the time this is
            logged. None if not yet available (e.g. logged at
            order-placement time, before the fill is confirmed).
        orders_executed_path: Override path (tests use tmp_path).

    Returns:
        True if the record was written, False if the write failed
        (never raises).
    """
    path = orders_executed_path or ORDERS_EXECUTED_PATH
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "order": order,
        "decision": decision,
        "gate_result": gate_result,
        "trade_execution_result": trade_execution_result,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return True
    except OSError:
        return False
