#!/usr/bin/env python3
"""
rebalancer.py (Python Service)
=====================================

Purpose:
    Formalizes /rebalance + portfolio_action.py's informal drift/capital/
    account logic into a real engine: per-holding drift bands (not point
    targets), a risk-budget check against E1's risk_snapshot.json,
    Canada-aware account/tax placement, and an ordered sells-before-buys
    order-plan output. Never mutates any input file — owns
    data/rebalance_plan.json exclusively. See docs/superpowers/specs/
    2026-07-09-rebalancer-v2-design.md.

Layer: Backend / Python Services / Rebalancer

Usage:
    python3 rebalancer.py --pretty
    python3 rebalancer.py --no-save --pretty
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

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
RISK_SNAPSHOT_PATH = DATA_DIR / "risk_snapshot.json"
THESIS_BREAKER_STATE_PATH = DATA_DIR / "thesis_breaker_state.json"
ACCOUNT_POLICY_PATH = DATA_DIR / "account_policy.json"
PROJECTIONS_DIR = DATA_DIR / "projections"
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


def get_latest_valuation_action(ticker: str, projections_dir: Path) -> str | None:
    """Latest AI projection's aiThesis.action for a ticker, or None if unavailable.

    Mirrors portfolio_action.py's _load_ai_upside() latest-AI_AGENT-projection
    selection, but returns the raw action string instead of computed upside —
    this is the actual "EXIT/SELL-gated" signal the rebalancer must never buy
    against (not derive_action()'s portfolio-weight ratio label).

    Args:
        ticker: Ticker to look up.
        projections_dir: Path to data/projections/.

    Returns:
        The latest AI_AGENT projection's aiThesis.action, or None if the
        projection file is missing, empty, or malformed.
    """
    path = projections_dir / f"{ticker}.json"
    if not path.exists():
        return None
    try:
        projs = json.loads(path.read_text())
        if isinstance(projs, list):
            if not projs:
                return None
            ai = [p for p in projs if p.get("source") == "AI_AGENT"]
            proj = max(ai, key=lambda x: x.get("savedAt", "")) if ai else projs[0]
        else:
            proj = projs
        return proj.get("aiThesis", {}).get("action")
    except Exception:
        return None


def compute_candidate_orders(
    bands: dict[str, dict[str, Any]],
    target_data: dict[str, Any],
    prices: dict[str, float],
    total_usd: float,
    projections_dir: Path,
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
        projections_dir: Path to data/projections/.

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
        valuation_action = get_latest_valuation_action(ticker, projections_dir)
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
    portfolio_path: Path = PORTFOLIO_PATH,
) -> tuple[dict[str, dict[str, dict[str, float | None]]], dict[str, float], dict[str, str]]:
    """Per-account share/cost-basis positions, preferring real tvSnapshot data.

    Reads portfolio.json's tvSnapshot.snapshots[].positions for real
    per-account splits (with avgFillPrice as cost basis) when present. Falls
    back to mirroring TFSA at ~1/3 share count for RRSP (this repo's
    documented account structure) for any account tvSnapshot doesn't cover.

    Args:
        portfolio_path: Path to portfolio.json.

    Returns:
        (account_positions, account_cash_usd, account_source) —
        account_positions[account][ticker] = {"shares", "costBasis"};
        account_cash_usd[account] is that account's USD cash balance (a
        separate dict, not folded into account_positions — see this
        function's Interfaces note on why); account_source[account] is
        "tvSnapshot" or "heuristic_1_3_mirror".
    """
    raw = json.loads(Path(portfolio_path).read_text())
    snapshots = (raw.get("tvSnapshot") or {}).get("snapshots", [])

    positions: dict[str, dict[str, dict[str, float | None]]] = {}
    cash_usd: dict[str, float] = {}
    source: dict[str, str] = {}
    synced_accounts: set[str] = set()

    for snap in snapshots:
        acct = snap.get("accountType")
        if not acct:
            continue
        synced_accounts.add(acct)
        acct_positions: dict[str, dict[str, float | None]] = {}
        for p in snap.get("positions", []):
            sym = normalize_ticker(p.get("symbol", ""))
            if not sym:
                continue
            acct_positions[sym] = {
                "shares": float(p.get("quantity") or 0),
                "costBasis": float(p["avgFillPrice"]) if p.get("avgFillPrice") else None,
            }
        balances = snap.get("balances", {})
        cash_usd[acct] = float(balances.get("cashUSDCombined") or balances.get("cashUSD") or 0)
        positions[acct] = acct_positions
        source[acct] = "tvSnapshot"

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebalance order plan")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"status": "scaffold — orchestrator added in Task 8"}, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
