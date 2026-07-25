#!/usr/bin/env python3
"""
rebalancer.py - Python utility script.

Purpose:
    Formalizes /rebalance + portfolio_action.py's informal drift/capital/
    account logic into a real engine: per-holding drift bands (not point
    targets), a risk-budget check against E1's risk_snapshot.json,
    Canada-aware account/tax placement, and an ordered sells-before-buys
    order-plan output. Never mutates any input file — owns
    data/rebalance_plan.json exclusively. See docs/superpowers/specs/
    2026-07-09-rebalancer-v2-design.md.

Layer:
    Backend / Python Services

Usage Examples:
    python3 rebalancer.py --pretty
    python3 rebalancer.py --no-save --pretty

Key Functions (Index):
    - compute_bands()
    - get_latest_valuation_action()
    - compute_candidate_orders()
    - load_account_positions()
    - compute_account_routing()
    - preferred_account()
    - compute_capital_gains_estimate()
    - compute_risk_budget_check()
    - compute_breaker_warnings()
    - _now_iso()
    - _check_no_trade_conditions()
    - _build_order_entries()
    - compute_rebalance_plan()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portfolio_io import load_portfolio_state, compute_weights  # noqa: E402
from ticker_aliases import normalize_ticker  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import list_accounts  # noqa: E402
from domain_model.account_investment_repository import list_account_investments  # noqa: E402
from domain_model.investment_repository import get_investment  # noqa: E402
from domain_model.portfolio_repository import get_last_synced_at  # noqa: E402
from domain_model.portfolio_policy_repository import get_portfolio_policy  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection,
    get_latest_projection_by_source,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
RISK_SNAPSHOT_PATH = DATA_DIR / "risk_snapshot.json"
THESIS_BREAKER_STATE_PATH = DATA_DIR / "thesis_breaker_state.json"
# DEPRECATED, unused: account_policy.json was archived (git mv) in Wave 5E. This
# default now points at a file that no longer exists -- kept only for
# compute_rebalance_plan()'s account_policy_path parameter's signature
# compatibility (see that function's docstring). Do not read this path.
ACCOUNT_POLICY_PATH = DATA_DIR / "account_policy.json"
DB_PATH = DATA_DIR / "domain_model.sqlite"
REBALANCE_PLAN_PATH = DATA_DIR / "rebalance_plan.json"

DEFAULT_BAND_CONFIG: dict[str, float] = {"relativePct": 20.0, "absolutePct": 1.5, "criticalMultiplier": 2.0}


def compute_bands(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    band_config: dict[str, float] = DEFAULT_BAND_CONFIG,
) -> dict[str, dict[str, Any]]:
    """Per-holding no-churn band: max(relative %, absolute pp) around targetWeight.

    A holding whose actual drift falls within its band gets no rebalance
    order generated this run — this is what kills churn/small-order noise
    vs. a flat point-target comparison.

    Args:
        current_weights: {ticker: weight_pct} (0-100 scale), actual broker weights.
        target_weights: {ticker: weight_pct} (0-100 scale), from target-portfolio.json.
        band_config: {"relativePct": float, "absolutePct": float} — band =
            max(targetWeight * relativePct/100, absolutePct).

    Returns:
        {ticker: {"currentWeight", "targetWeight", "bandPct", "driftPct", "inBand"}}
        for the union of tickers in either input (a ticker missing from one
        side is treated as 0.0 on that side).
    """
    tickers = set(current_weights) | set(target_weights)
    result: dict[str, dict[str, Any]] = {}
    for t in tickers:
        current = current_weights.get(t, 0.0)
        target = target_weights.get(t, 0.0)
        drift = current - target
        band_pct = max(target * band_config["relativePct"] / 100.0, band_config["absolutePct"])
        result[t] = {
            "currentWeight": round(current, 4),
            "targetWeight": round(target, 4),
            "bandPct": round(band_pct, 4),
            "driftPct": round(drift, 4),
            "inBand": abs(drift) <= band_pct,
        }
    return result


def _resolve_investment_id_readonly(conn, ticker: str) -> str | None:
    """Look up an existing investment's id by symbol without creating one.

    Read-only lookup (mirrors apply_catalyst.py's helper of the same name) —
    a ticker with no `investment` row is treated the same as "no projection
    file on disk" was in the original file-based code, not an error.
    """
    cursor = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_latest_valuation_action(ticker: str, db_path: Path) -> str | None:
    """Latest AI projection's action for a ticker, or None if unavailable.

    Storage backend (Wave 1 Task 7A): reads `projection_version` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json`
    directly (ADR-029). Mirrors portfolio_action.py's `_load_ai_upside()`
    latest-AI_AGENT-projection selection (Task 6 finding: prefer
    `get_latest_projection_by_source(..., "AI_AGENT")` over `MAX(version)`,
    since version numbers are not always chronological) — this is the actual
    "EXIT/SELL-gated" signal the rebalancer must never buy against (not
    derive_action()'s portfolio-weight ratio label).

    Args:
        ticker: Ticker to look up.
        db_path: Path to domain_model.sqlite.

    Returns:
        The latest AI_AGENT projection's action, or the latest projection of
        any source if no AI_AGENT row exists, or None if the investment has
        no projection rows at all.
    """
    try:
        conn = initialize_db(str(db_path))
        try:
            investment_id = _resolve_investment_id_readonly(conn, ticker)
            if investment_id is None:
                return None
            entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
            if entry is None:
                entry = get_latest_projection(conn, investment_id)
            if entry is None:
                return None
            return entry.get("action")
        finally:
            conn.close()
    except Exception:
        return None


def compute_candidate_orders(
    bands: dict[str, dict[str, Any]],
    target_data: dict[str, Any],
    prices: dict[str, float],
    total_usd: float,
    db_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Turn out-of-band holdings into raw candidate orders (pre-account-routing).

    Applies the hard-rule exclusions that remove an order entirely (never
    warnings): never buys an EXIT/SELL-rated holding, never buys above
    targetEntryPrice, and downgrades to a no-op when a standingDecision is
    present (same "signal stands but no trade proposed without your
    direction" framing brief_recommendations.py already uses for EXIT/REDUCE).
    Sells are never gated — an overweight EXIT-rated or standing-decision
    holding should still be trimmed toward target.

    Args:
        bands: Output of compute_bands().
        target_data: Parsed target-portfolio.json (targetEntryPrice,
            standingDecision per holding).
        prices: {ticker: current_price}.
        total_usd: Broker-authoritative portfolio total (never shares×price).
        db_path: Path to domain_model.sqlite.

    Returns:
        (candidate_orders, skipped_restores).
    """
    holdings_by_ticker = {h["ticker"]: h for h in target_data.get("holdings", [])}
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for ticker, band in bands.items():
        if band["inBand"]:
            continue
        price = prices.get(ticker)
        if not price or price <= 0:
            continue
        holding = holdings_by_ticker.get(ticker, {})
        drift_dollars = abs(band["driftPct"]) / 100.0 * total_usd
        shares = math.floor(drift_dollars / price)

        if band["driftPct"] > 0:
            if shares <= 0:
                continue
            candidates.append({
                "ticker": ticker, "action": "sell", "shares": shares,
                "currentWeight": band["currentWeight"], "targetWeight": band["targetWeight"],
            })
            continue

        # Buy-side hard gates are evaluated before the zero-share check so a
        # skip reason is still recorded even when the drift-dollar amount
        # floors to 0 shares at the current price (e.g. high-priced tickers).
        valuation_action = get_latest_valuation_action(ticker, db_path)
        if valuation_action in ("EXIT", "SELL"):
            skipped.append({"ticker": ticker, "reason": f"{valuation_action}-rated — not restoring"})
            continue

        entry_cap = holding.get("targetEntryPrice")
        if entry_cap is not None and price > entry_cap:
            skipped.append({
                "ticker": ticker,
                "reason": f"Price ${price:.2f} above targetEntryPrice ${entry_cap:.2f}",
            })
            continue

        standing = holding.get("standingDecision")
        if standing:
            skipped.append({
                "ticker": ticker,
                "reason": f"Standing decision ({standing.get('type', 'USER')}): "
                          f"{standing.get('reason', '')} Signal stands but no trade "
                          f"proposed without your direction.",
            })
            continue

        if shares <= 0:
            continue

        candidates.append({
            "ticker": ticker, "action": "buy", "shares": shares,
            "currentWeight": band["currentWeight"], "targetWeight": band["targetWeight"],
        })

    return candidates, skipped


def load_account_positions(
    db_path: Path = DB_PATH,
) -> tuple[dict[str, dict[str, dict[str, float | None]]], dict[str, float], dict[str, str]]:
    """Per-account share/cost-basis positions from domain_model.sqlite.

    Wave 3 cutover: per-account splits are read from ``account_investment``
    (joined to ``investment`` for the symbol) via
    ``account_investment_repository.list_account_investments`` — the exact shape
    the old portfolio.json ``tvSnapshot.snapshots[].positions`` block carried
    (quantity → shares, average_cost → costBasis). Cash is the ``CASH_USD``
    row's quantity (Wave 0 decision 5), kept as a separate per-account dict.
    Falls back to mirroring TFSA at ~1/3 share count for RRSP (this repo's
    documented account structure) only when RRSP has no rows of its own.

    Args:
        db_path: Path to domain_model.sqlite.

    Returns:
        (account_positions, account_cash_usd, account_source) —
        account_positions[account][ticker] = {"shares", "costBasis"};
        account_cash_usd[account] is that account's USD cash balance (a
        separate dict, not folded into account_positions — see this
        function's Interfaces note on why); account_source[account] is
        "sqlite" or "heuristic_1_3_mirror".
    """
    conn = initialize_db(str(db_path))
    try:
        accounts = list_accounts(conn)

        positions: dict[str, dict[str, dict[str, float | None]]] = {}
        cash_usd: dict[str, float] = {}
        source: dict[str, str] = {}
        synced_accounts: set[str] = set()

        for account_row in accounts:
            acct = account_row["account_id"]
            ai_rows = list_account_investments(conn, account_id=acct)
            if not ai_rows:
                continue  # an account with no holdings is treated as un-synced
            acct_positions: dict[str, dict[str, float | None]] = {}
            acct_cash = 0.0
            for row in ai_rows:
                investment = get_investment(conn, row["investment_id"])
                raw_symbol = investment["symbol"] if investment else row["investment_id"]
                if raw_symbol == "CASH_USD":
                    acct_cash = float(row["quantity"] or 0)
                    continue
                sym = normalize_ticker(raw_symbol)
                if not sym:
                    continue
                avg_cost = row["average_cost"]
                acct_positions[sym] = {
                    "shares": float(row["quantity"] or 0),
                    "costBasis": float(avg_cost) if avg_cost is not None else None,
                }
            synced_accounts.add(acct)
            positions[acct] = acct_positions
            cash_usd[acct] = acct_cash
            source[acct] = "sqlite"
    finally:
        conn.close()

    if synced_accounts and "RRSP" not in synced_accounts and "TFSA" in positions:
        rrsp_positions: dict[str, dict[str, float | None]] = {}
        for sym, pos in positions["TFSA"].items():
            mirrored = math.floor(pos["shares"] / 3)
            if mirrored > 0:
                rrsp_positions[sym] = {"shares": float(mirrored), "costBasis": pos["costBasis"]}
        positions["RRSP"] = rrsp_positions
        cash_usd["RRSP"] = 0.0
        source["RRSP"] = "heuristic_1_3_mirror"

    return positions, cash_usd, source


def compute_account_routing(
    candidate_orders: list[dict[str, Any]],
    account_positions: dict[str, dict[str, dict[str, float | None]]],
    account_cash_usd: dict[str, float],
    account_policy: dict[str, Any],
    target_data: dict[str, Any],
    prices: dict[str, float],
) -> list[dict[str, Any]]:
    """Assign each candidate order to an account, sequenced sells-before-buys.

    Sells route to whichever account(s) actually hold shares, split
    proportionally to shares held when more than one account holds the
    ticker. Buys route per accountPreferenceRules matched against the
    holding's role/pillarId tags, falling back to "default". A buy needing
    more cash than is available in its target account triggers a
    same-account PSU-U.TO trim sized via ceil(shortfall / psu_price)
    (never cross-account, per psuFundingRule).

    Args:
        candidate_orders: Output of compute_candidate_orders().
        account_positions: Output of load_account_positions() (the positions
            dict — first element of its 3-tuple return).
        account_cash_usd: Output of load_account_positions() (the cash dict —
            second element of its 3-tuple return).
        account_policy: Parsed account_policy.json.
        target_data: Parsed target-portfolio.json (role/pillarId per holding).
        prices: {ticker: current_price}.

    Returns:
        Ordered list of per-account orders — sells first (by ticker), then
        buys (by ticker); each order has an "account" key, and PSU-funded
        buys get a preceding synthetic PSU-U.TO sell order in the same
        account.
    """
    holdings_by_ticker = {h["ticker"]: h for h in target_data.get("holdings", [])}
    rules = account_policy.get("accountPreferenceRules", [])
    psu_rule = account_policy.get("psuFundingRule", {})
    psu_ticker = psu_rule.get("ticker", "PSU-U.TO")

    def preferred_account(ticker: str) -> str:
        holding = holdings_by_ticker.get(ticker, {})
        tags = {holding.get("role"), holding.get("pillarId")}
        for rule in rules:
            if rule.get("match") in tags:
                return rule["prefer"]
        return next((r["prefer"] for r in rules if r.get("match") == "default"), "TFSA")

    sells = [o for o in candidate_orders if o["action"] == "sell"]
    buys = [o for o in candidate_orders if o["action"] == "buy"]
    routed: list[dict[str, Any]] = []

    for order in sorted(sells, key=lambda o: o["ticker"]):
        ticker = order["ticker"]
        held = {
            acct: pos[ticker]["shares"]
            for acct, pos in account_positions.items()
            if ticker in pos and pos[ticker]["shares"] > 0
        }
        if not held:
            continue
        total_held = sum(held.values())
        remaining = min(order["shares"], total_held)
        allocated: list[dict[str, Any]] = []
        for acct, held_shares in sorted(held.items(), key=lambda kv: -kv[1]):
            acct_shares = min(remaining, held_shares, math.floor(order["shares"] * held_shares / total_held))
            if acct_shares > 0:
                allocated.append({**order, "account": acct, "shares": acct_shares})
                remaining -= acct_shares
        if remaining > 0 and allocated:
            # Distribute rounding remainder to accounts with headroom (largest
            # holder first, since `allocated` preserves the descending sort),
            # never pushing any single account past its own held_shares cap.
            for entry in allocated:
                headroom = held[entry["account"]] - entry["shares"]
                if headroom <= 0:
                    continue
                add = min(remaining, headroom)
                entry["shares"] += add
                remaining -= add
                if remaining <= 0:
                    break
        routed.extend(allocated)

    available_cash: dict[str, float] = dict(account_cash_usd)
    for order in routed:
        price = prices.get(order["ticker"], 0.0)
        available_cash[order["account"]] = available_cash.get(order["account"], 0.0) + order["shares"] * price

    for order in sorted(buys, key=lambda o: o["ticker"]):
        ticker = order["ticker"]
        acct = preferred_account(ticker)
        price = prices.get(ticker, 0.0)
        cost = order["shares"] * price
        cash_here = available_cash.get(acct, 0.0)
        if cost > cash_here and ticker != psu_ticker:
            shortfall = cost - cash_here
            psu_price = prices.get(psu_ticker, 100.0)
            psu_held = account_positions.get(acct, {}).get(psu_ticker, {}).get("shares", 0.0)
            psu_shares = math.ceil(shortfall / psu_price)
            if psu_held >= psu_shares:
                routed.append({
                    "ticker": psu_ticker, "action": "sell", "account": acct,
                    "shares": psu_shares,
                    "rationale": f"Same-account funding for {ticker} buy",
                })
                available_cash[acct] = cash_here + psu_shares * psu_price
        routed.append({**order, "account": acct})
        available_cash[acct] = available_cash.get(acct, 0.0) - cost

    return routed


def compute_capital_gains_estimate(
    ticker: str,
    account: str,
    shares_sold: float,
    sale_price: float,
    account_positions: dict[str, dict[str, dict[str, float | None]]],
) -> float | None:
    """Estimate capital gains/loss for a Cash-account sell.

    TFSA/RRSP gains are never taxed, so this returns None for any account
    other than "Cash" without even attempting a cost-basis lookup. Forward-
    looking: the user's current accounts are TFSA/RRSP only, so this path is
    fixture-tested but not yet exercised against real data (spec §8).

    Args:
        ticker: Ticker being sold.
        account: Account name the sell is routed to.
        shares_sold: Shares in this sell order.
        sale_price: Current price used for the sell.
        account_positions: Output of load_account_positions() (positions
            only) — used for cost basis in the same account.

    Returns:
        (sale_price - cost_basis) * shares_sold, or None if the account
        isn't "Cash" or cost basis is unavailable.
    """
    if account != "Cash":
        return None
    cost_basis = account_positions.get(account, {}).get(ticker, {}).get("costBasis")
    if cost_basis is None:
        return None
    return round((sale_price - cost_basis) * shares_sold, 2)


def compute_risk_budget_check(
    routed_orders: list[dict[str, Any]],
    bands: dict[str, dict[str, Any]],
    risk_snapshot: dict[str, Any] | None,
    account_policy: dict[str, Any],
    target_data: dict[str, Any],
) -> dict[str, list[str]]:
    """Warn (never exclude) when a proposed buy would push MRC/cluster over cap.

    This is a deliberate design decision (spec §6.1): real veto power belongs
    to a later, separate component. This function only ever attaches warning
    strings to an order — it never removes or excludes one.

    First-order estimate only: scales the ticker's existing
    marginalRiskContribution by its proposed weight ratio (target/current)
    rather than re-running risk_engine.py against hypothetical post-trade
    weights (out of scope — spec §6.1). Labeled as an estimate in the
    warning text. Degrades to {} when risk_snapshot is None.

    A ticker with currentWeight == 0.0 (e.g. a fresh INITIATE buy with no
    prior position) has no valid target/current ratio to scale from, so the
    MRC projection is skipped for that ticker rather than dividing by zero —
    the cluster-variance check still runs independently for it.

    Args:
        routed_orders: Output of compute_account_routing() (only buys matter).
        bands: Output of compute_bands() (for currentWeight/targetWeight).
        risk_snapshot: Parsed risk_snapshot.json, or None if unavailable.
        account_policy: Parsed account_policy.json (riskBudgetCaps).
        target_data: Parsed target-portfolio.json (pillarId per holding).

    Returns:
        {ticker: [warning strings]} — only tickers with at least one warning.
    """
    if not risk_snapshot:
        return {}
    mrc = risk_snapshot.get("marginalRiskContribution", {})
    cluster = {c["pillarId"]: c for c in risk_snapshot.get("clusterExposure", [])}
    caps = account_policy.get("riskBudgetCaps", {})
    mrc_cap = caps.get("maxMarginalRiskContributionPct", 25)
    cluster_cap = caps.get("maxClusterVarianceContributionPct", 60)
    pillar_map = {h["ticker"]: h.get("pillarId", "unassigned") for h in target_data.get("holdings", [])}

    warnings: dict[str, list[str]] = {}
    for order in routed_orders:
        if order["action"] != "buy":
            continue
        ticker = order["ticker"]
        band = bands.get(ticker, {})
        current_w, target_w = band.get("currentWeight", 0.0), band.get("targetWeight", 0.0)
        old_mrc = mrc.get(ticker)
        if old_mrc is not None and current_w > 0:
            projected_mrc_pct = old_mrc * 100 * (target_w / current_w)
            if projected_mrc_pct > mrc_cap:
                warnings.setdefault(ticker, []).append(
                    f"Estimated MRC would reach {projected_mrc_pct:.1f}% (estimate) > {mrc_cap}% cap"
                )
        pillar = pillar_map.get(ticker, "unassigned")
        cluster_entry = cluster.get(pillar)
        if cluster_entry and cluster_entry.get("varianceContributionPct", 0) > cluster_cap:
            warnings.setdefault(ticker, []).append(
                f"Pillar '{pillar}' cluster variance already "
                f"{cluster_entry['varianceContributionPct']:.1f}% > {cluster_cap}% cap"
            )
    return warnings


def compute_breaker_warnings(
    routed_orders: list[dict[str, Any]],
    thesis_breaker_state: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Flag (never suppress) a proposed buy on a ticker with a TRIGGERED breaker.

    Visibility escalation only, matching B5's own posture — this never
    removes a buy order from the plan, only attaches a warning string.

    Args:
        routed_orders: Output of compute_account_routing().
        thesis_breaker_state: Parsed thesis_breaker_state.json, or None.

    Returns:
        {ticker: [warning strings]} for buy orders on tickers with at least
        one TRIGGERED breaker. Degrades to {} if state is missing.
    """
    if not thesis_breaker_state:
        return {}
    holdings_state = thesis_breaker_state.get("holdings", {})
    warnings: dict[str, list[str]] = {}
    for order in routed_orders:
        if order["action"] != "buy":
            continue
        ticker = order["ticker"]
        for breaker_id, entry in holdings_state.get(ticker, {}).items():
            if entry.get("status") == "TRIGGERED":
                warnings.setdefault(ticker, []).append(
                    f"TRIGGERED breaker '{breaker_id}': current value "
                    f"{entry.get('currentValue')!r}, streak {entry.get('currentStreak')}"
                )
    return warnings


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a literal 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _has_any_projection(db_path: Path, ticker: str) -> bool:
    """True if `ticker` has at least one `projection_version` row (any source).

    Existence-only check for `_check_no_trade_conditions`'s missing-valuations
    gate — this does NOT need the AI_AGENT-vs-any-source distinction that
    `get_latest_valuation_action` needs, it only needs "has a DCF projection
    ever been recorded", mirroring the original file-based `.exists()` check.
    """
    try:
        conn = initialize_db(str(db_path))
        try:
            investment_id = _resolve_investment_id_readonly(conn, ticker)
            if investment_id is None:
                return False
            return get_latest_projection(conn, investment_id) is not None
        finally:
            conn.close()
    except Exception:
        return False


def _check_no_trade_conditions(
    target_data: dict[str, Any], portfolio_path: Path, db_path: Path,
) -> str | None:
    """Returns a blockedReason string, or None if clear to trade.

    Checks (in order): portfolio-data staleness (>60min), target weights not
    summing to 100%±0.5%, >30% of thesis holdings missing a DCF projection.

    Args:
        target_data: Parsed target-portfolio.json.
        portfolio_path: Retained for signature compatibility; no longer read
            (Wave 3 cutover — staleness now derives from SQLite).
        db_path: Path to domain_model.sqlite.

    Returns:
        A human-readable blockedReason, or None.
    """
    # Wave 3 cutover: freshness is the most-recent account_investment sync time
    # (MAX(last_synced_at)), not portfolio.json's totals.timestamp.
    conn = initialize_db(str(db_path))
    try:
        ts = get_last_synced_at(conn)
    finally:
        conn.close()
    if ts:
        age_minutes = (
            datetime.now(timezone.utc) - datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ).total_seconds() / 60
        if age_minutes > 60:
            return f"DATA_STALE — portfolio data is {age_minutes:.0f} min old (run /tv-portfolio-sync first)"

    holdings = target_data.get("holdings", [])
    weight_sum = sum(h.get("targetWeight", 0.0) for h in holdings)
    if abs(weight_sum - 100) > 0.5:
        return f"TARGETS_INVALID — target weights sum to {weight_sum:.1f}% (must be 100%)"

    thesis_tickers = [h for h in holdings if h.get("targetWeight", 0) > 0]
    if thesis_tickers:
        missing = sum(1 for h in thesis_tickers if not _has_any_projection(db_path, h["ticker"]))
        if missing / len(thesis_tickers) > 0.3:
            return f"MISSING_VALUATIONS — {missing}/{len(thesis_tickers)} thesis holdings have no DCF projection"

    return None


def _build_order_entries(
    routed: list[dict[str, Any]],
    bands: dict[str, dict[str, Any]],
    prices: dict[str, float],
    account_positions: dict[str, dict[str, dict[str, float | None]]],
    risk_warnings: dict[str, list[str]],
    breaker_warnings: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Attach rationale, gates, and warnings to each routed order for the final plan.

    Split out of compute_rebalance_plan() to keep the orchestrator itself
    focused on sequencing the seven sub-functions (Google-style docstring
    convention: refactor at 50+ lines).

    Args:
        routed: Output of compute_account_routing().
        bands: Output of compute_bands() (for the default drift rationale).
        prices: {ticker: current_price}.
        account_positions: Output of load_account_positions() (positions dict
            — first element of its 3-tuple return).
        risk_warnings: Output of compute_risk_budget_check().
        breaker_warnings: Output of compute_breaker_warnings().

    Returns:
        Orders in the shape rebalance_plan.json's "orders" field expects.
    """
    orders: list[dict[str, Any]] = []
    for order in routed:
        ticker = order["ticker"]
        band = bands.get(ticker, {})
        price = prices.get(ticker, 0.0)
        capital_gains = None
        if order["action"] == "sell":
            capital_gains = compute_capital_gains_estimate(
                ticker, order["account"], order["shares"], price, account_positions
            )
        # Only compute_account_routing's synthetic PSU-funding sell pre-sets
        # "rationale" — every normal candidate-derived order does not, so this
        # (not "driftPct" in band, which PSU-U.TO's own real band entry would
        # also satisfy) is the correct way to tell them apart.
        is_psu_funding_order = "rationale" in order
        gates = ["psu_funding_rule"] if is_psu_funding_order else ["band_check"]
        if order["action"] == "buy":
            gates += ["not_exit_or_sell_rated", "below_target_entry_price"]
        orders.append({
            "ticker": ticker,
            "action": order["action"],
            "account": order["account"],
            "shares": order["shares"],
            "rationale": order.get("rationale") or (
                f"Out of band: {band.get('driftPct', 0):+.1f}pp vs {band.get('bandPct', 0):.1f}pp band"
            ),
            "gatesPassed": gates,
            "riskGateWarnings": risk_warnings.get(ticker, []),
            "breakerWarnings": breaker_warnings.get(ticker, []),
            "capitalGainsEstimate": capital_gains,
        })
    return orders


def _load_account_policy_from_db(db_path: Path) -> dict[str, Any]:
    """Read the account/portfolio policy from portfolio_policy (Wave 5E cutover),
    reshaped into the same dict shape account_policy.json used to provide
    (accountPreferenceRules/psuFundingRule/riskBudgetCaps/bandConfig) -- so every
    downstream function in this file (compute_account_routing,
    compute_risk_budget_check, etc.) needs no changes.

    Returns an empty-shaped dict (each key present, values empty/defaulted) if
    portfolio_policy has never been written, matching the graceful-degradation
    behavior callers already rely on via account_policy.get(key, {}).
    """
    conn = initialize_db(str(db_path))
    try:
        row = get_portfolio_policy(conn)
    finally:
        conn.close()
    if row is None:
        return {}
    return {
        "accountPreferenceRules": json.loads(row["account_preference_rules_json"] or "[]"),
        "psuFundingRule": json.loads(row["psu_funding_rule_json"] or "{}"),
        "riskBudgetCaps": {
            "maxMarginalRiskContributionPct": row["max_marginal_risk_contribution_pct"],
            "maxClusterVarianceContributionPct": row["max_cluster_variance_contribution_pct"],
        },
        "bandConfig": {
            "relativePct": row["rebalance_band_relative_pct"],
            "absolutePct": row["rebalance_band_absolute_pct"],
            "criticalMultiplier": row["rebalance_band_critical_multiplier"],
        },
    }


def compute_rebalance_plan(
    target_portfolio_path: Path = TARGET_PATH,
    portfolio_path: Path = PORTFOLIO_PATH,
    risk_snapshot_path: Path = RISK_SNAPSHOT_PATH,
    thesis_breaker_state_path: Path = THESIS_BREAKER_STATE_PATH,
    account_policy_path: Path = ACCOUNT_POLICY_PATH,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """Primary orchestrator — builds the full rebalance order plan.

    Never mutates any input file — owns data/rebalance_plan.json exclusively
    (main()'s --no-save-gated write). Checks no-trade conditions first; if
    any fire, returns early with blockedReason set and orders: [].

    Args:
        target_portfolio_path: Path to target-portfolio.json.
        portfolio_path: Path to portfolio.json.
        risk_snapshot_path: Path to risk_snapshot.json (E1 output).
        thesis_breaker_state_path: Path to thesis_breaker_state.json (B5 output).
        account_policy_path: DEPRECATED, unused since Wave 5E's cutover to
            _load_account_policy_from_db(db_path) below -- account_policy.json is
            archived (git mv) and this default now points at a file that no longer
            exists. Kept only so every already-migrated call site (tests, CLI)
            keeps working without another signature change; do not rely on this
            parameter having any effect.
        db_path: Path to domain_model.sqlite.

    Returns:
        The full rebalance plan dict — see docs/superpowers/specs/
        2026-07-09-rebalancer-v2-design.md §3.3 for the field-by-field shape.
    """
    target_data = json.loads(Path(target_portfolio_path).read_text())
    account_policy = _load_account_policy_from_db(db_path)

    blocked = _check_no_trade_conditions(target_data, Path(portfolio_path), Path(db_path))
    if blocked:
        return {
            "generatedAt": _now_iso(), "blockedReason": blocked, "bands": {},
            "orders": [], "skippedRestores": [], "accountDataSource": {}, "warnings": [],
        }

    warnings: list[str] = []
    state = load_portfolio_state(Path(portfolio_path))
    current_weights = compute_weights(state["shares"], state["prices"], state["total_usd"])
    target_weights = {h["ticker"]: h.get("targetWeight", 0.0) for h in target_data.get("holdings", [])}
    band_config = account_policy.get("bandConfig", DEFAULT_BAND_CONFIG)

    bands = compute_bands(current_weights, target_weights, band_config)
    candidates, skipped = compute_candidate_orders(
        bands, target_data, state["prices"], state["total_usd"], Path(db_path)
    )

    account_positions, account_cash_usd, account_source = load_account_positions(Path(db_path))
    routed = compute_account_routing(
        candidates, account_positions, account_cash_usd, account_policy, target_data, state["prices"]
    )

    risk_snapshot = None
    if Path(risk_snapshot_path).exists():
        risk_snapshot = json.loads(Path(risk_snapshot_path).read_text())
    else:
        warnings.append("risk_snapshot.json not found — risk-budget check skipped")
    risk_warnings = compute_risk_budget_check(routed, bands, risk_snapshot, account_policy, target_data)

    breaker_state = None
    if Path(thesis_breaker_state_path).exists():
        breaker_state = json.loads(Path(thesis_breaker_state_path).read_text())
    else:
        warnings.append("thesis_breaker_state.json not found — breaker check skipped")
    breaker_warnings = compute_breaker_warnings(routed, breaker_state)

    orders = _build_order_entries(
        routed, bands, state["prices"], account_positions, risk_warnings, breaker_warnings
    )

    return {
        "generatedAt": _now_iso(),
        "blockedReason": None,
        "bands": bands,
        "orders": orders,
        "skippedRestores": skipped,
        "accountDataSource": account_source,
        "warnings": warnings,
    }


def main() -> None:
    """CLI entry point — computes the rebalance plan and prints/saves it.

    Writes data/rebalance_plan.json unless --no-save is passed. Never
    mutates any input file (spec §3.3).
    """
    parser = argparse.ArgumentParser(description="Rebalance order plan")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing rebalance_plan.json")
    args = parser.parse_args()

    plan = compute_rebalance_plan()
    if not args.no_save:
        REBALANCE_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REBALANCE_PLAN_PATH, "w") as f:
            json.dump(plan, f, indent=2)

    print(json.dumps(plan, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
