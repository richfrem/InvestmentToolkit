#!/usr/bin/env python3
"""
risk_officer.py - Python utility script.

Purpose:
    Turns E2's warn-only riskGateWarnings/breakerWarnings (the stored rebalance plan)
    into real veto power. Reuses E2's exact thresholds — an order is vetoed
    iff either warning list is non-empty; no new numeric caps are introduced.
    Reads only the stored rebalance plan (the breaker warnings in it come from the evaluated
    breaker state in domain_model.sqlite) and never mutates it. Owns the stored
    risk_officer_review and risk_officer_override snapshots exclusively. See docs/superpowers/specs/
    2026-07-10-g2-risk-officer-red-team-design.md.

Layer:
    Backend / Python Services

Usage Examples:
    python3 risk_officer.py --pretty
    python3 risk_officer.py --log-override --ticker CORZ --action buy \
        --account TFSA --rationale "Conviction unchanged, MRC estimate is first-order only"

Key Functions (Index):
    - _now_iso()
    - classify_orders()
    - compute_risk_officer_review()
    - log_risk_officer_override()
    - _cli_log_override()
    - main()

Key Input Dependencies:
    - domain_model.sqlite computed_snapshot table (latest rebalance_plan)

Key Output Dependencies:
    - domain_model.sqlite computed_snapshot table (risk_officer_review, risk_officer_override)
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.computed_snapshot_repository import load_latest_snapshot, save_snapshot  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a literal 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def classify_orders(orders: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split the rebalance plan's orders into (vetoed, approved).

    An order is vetoed iff its riskGateWarnings or breakerWarnings list is
    non-empty — E2's existing warn-only signals, now enforced rather than
    merely displayed. No new numeric thresholds are introduced here.

    Args:
        orders: The "orders" list from the rebalance plan.

    Returns:
        (vetoed, approved). Vetoed entries are the input order dict plus a
        "vetoReasons" key (riskGateWarnings entries first, then
        breakerWarnings entries). Approved entries are returned unchanged
        (no "vetoReasons" key added).
    """
    vetoed: list[dict[str, Any]] = []
    approved: list[dict[str, Any]] = []
    for order in orders:
        risk_warnings = order.get("riskGateWarnings", [])
        breaker_warnings = order.get("breakerWarnings", [])
        if risk_warnings or breaker_warnings:
            vetoed.append({**order, "vetoReasons": risk_warnings + breaker_warnings})
        else:
            approved.append(order)
    return vetoed, approved


def compute_risk_officer_review(
    db_path: Path = DB_PATH,
    save: bool = True,
) -> dict[str, Any]:
    """Load the stored rebalance plan, classify its orders, store the review.

    Args:
        db_path: domain_model.sqlite holding the rebalance_plan snapshot and receiving
            the risk_officer_review snapshot.
        save: If False, compute and return without storing the review (mirrors
            rebalancer.py's --no-save pattern).

    Returns:
        {"status": "ok"|"no_plan"|"plan_blocked", "generatedAt",
         "sourceRebalancePlanGeneratedAt", "vetoedOrders", "approvedOrders"}.
        "no_plan" (no stored rebalance plan) and "plan_blocked"
        (the plan's blockedReason is non-null) both return empty order
        lists and store nothing — there is nothing to review yet.
    """
    conn = initialize_db(str(db_path))
    try:
        plan = load_latest_snapshot(conn, "rebalance_plan")
    finally:
        conn.close()
    if plan is None:
        return {"status": "no_plan", "vetoedOrders": [], "approvedOrders": []}
    if plan.get("blockedReason"):
        return {"status": "plan_blocked", "vetoedOrders": [], "approvedOrders": []}

    vetoed, approved = classify_orders(plan.get("orders", []))
    result = {
        "status": "ok",
        "generatedAt": _now_iso(),
        "sourceRebalancePlanGeneratedAt": plan.get("generatedAt"),
        "vetoedOrders": vetoed,
        "approvedOrders": approved,
    }
    if save:
        conn = initialize_db(str(db_path))
        try:
            save_snapshot(conn, "risk_officer_review", result)
        finally:
            conn.close()
    return result


def log_risk_officer_override(
    ticker: str,
    action: str,
    account: str,
    shares: float | None,
    veto_reasons: list[str],
    rationale: str,
    overridden_by: str = "user",
    db_path: Path = DB_PATH,
) -> None:
    """Append one accountability-trail record for a vetoed-order override.

    Called by risk-officer-agent.md — only a human decision to proceed with
    a vetoed order constitutes an "override." Append-only: one risk_officer_override
    snapshot per call.

    Args:
        ticker: Order's ticker.
        action: "buy" or "sell".
        account: Order's account (e.g. "TFSA").
        shares: Order's share count, or None if unknown.
        veto_reasons: The order's vetoReasons at time of override.
        rationale: The user's stated reason for proceeding anyway.
        overridden_by: Who made the call — defaults to "user".
        db_path: domain_model.sqlite receiving the override record.
    """
    entry = {
        "date": date.today().isoformat(),
        "ticker": ticker,
        "action": action,
        "account": account,
        "shares": shares,
        "vetoReasons": veto_reasons,
        "rationale": rationale,
        "overriddenBy": overridden_by,
    }
    conn = initialize_db(str(db_path))
    try:
        save_snapshot(conn, "risk_officer_override", entry)
    finally:
        conn.close()


def _cli_log_override(
    ticker: str,
    action: str,
    account: str,
    rationale: str,
    overridden_by: str = "user",
    db_path: Path = DB_PATH,
) -> None:
    """Resolve a vetoed order's shares/vetoReasons from the stored review, then log.

    Thin wrapper so a caller (risk-officer-agent.md, via --log-override) only
    needs a ticker/action/account/rationale — not the review's internal shape.

    Args:
        ticker: Order's ticker.
        action: "buy" or "sell".
        account: Order's account.
        rationale: The user's stated reason for proceeding anyway.
        overridden_by: Who made the call — defaults to "user".
        db_path: domain_model.sqlite holding the review and receiving the override.

    Raises:
        ValueError: If there is no stored review, or no vetoed order matches
            (ticker, action, account).
    """
    conn = initialize_db(str(db_path))
    try:
        review = load_latest_snapshot(conn, "risk_officer_review")
    finally:
        conn.close()
    if review is None:
        raise ValueError("no stored risk officer review — run risk_officer.py --pretty first")
    match = next(
        (
            o for o in review.get("vetoedOrders", [])
            if o["ticker"] == ticker and o["action"] == action and o["account"] == account
        ),
        None,
    )
    if match is None:
        raise ValueError(f"no vetoed order found for {ticker}/{action}/{account} in the stored review")
    log_risk_officer_override(
        ticker=ticker, action=action, account=account, shares=match.get("shares"),
        veto_reasons=match.get("vetoReasons", []), rationale=rationale,
        overridden_by=overridden_by, db_path=db_path,
    )


def main() -> None:
    """CLI entry point — compute the risk-officer review, or log an override.

    --log-override lets risk-officer-agent.md record a vetoed-order override
    without importing this module directly.
    """
    parser = argparse.ArgumentParser(description="Risk officer veto classification / override logging")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, do not store the review")
    parser.add_argument("--log-override", action="store_true", help="Log an override instead of reviewing")
    parser.add_argument("--ticker", help="Ticker (required with --log-override)")
    parser.add_argument("--action", choices=["buy", "sell"], help="Order action (required with --log-override)")
    parser.add_argument("--account", help="Account (required with --log-override)")
    parser.add_argument("--rationale", help="Override rationale (required with --log-override)")
    parser.add_argument("--overridden-by", default="user", help="Who made the override call")
    args = parser.parse_args()

    if args.log_override:
        if not (args.ticker and args.action and args.account and args.rationale):
            sys.exit("ERROR: --log-override requires --ticker, --action, --account, and --rationale")
        _cli_log_override(args.ticker, args.action, args.account, args.rationale, args.overridden_by)
        print(f"✅  Logged override for {args.ticker} {args.action} ({args.account})")
        return

    result = compute_risk_officer_review(save=not args.no_save)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
