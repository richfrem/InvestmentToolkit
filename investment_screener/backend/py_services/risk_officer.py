#!/usr/bin/env python3
"""
risk_officer.py (Python Service)
=====================================

Purpose:
    Turns E2's warn-only riskGateWarnings/breakerWarnings (rebalance_plan.json)
    into real veto power. Reuses E2's exact thresholds — an order is vetoed
    iff either warning list is non-empty; no new numeric caps are introduced.
    Never mutates rebalance_plan.json, risk_snapshot.json, or
    thesis_breaker_state.json — read-only on all three. Owns
    data/risk_officer_review.json and data/risk_officer_overrides.jsonl
    exclusively. See docs/superpowers/specs/
    2026-07-10-g2-risk-officer-red-team-design.md.

Layer: Backend / Python Services / Risk

Usage:
    python3 risk_officer.py --pretty
    python3 risk_officer.py --log-override --ticker CORZ --action buy \
        --account TFSA --rationale "Conviction unchanged, MRC estimate is first-order only"

Key Functions:
    - classify_orders() - Splits rebalance_plan.json's orders into (vetoed, approved)
    - compute_risk_officer_review() - Primary orchestrator: plan -> risk_officer_review.json
    - log_risk_officer_override() - Appends one accountability-trail record for an override

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Validates position risk limits)
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
REBALANCE_PLAN_PATH = DATA_DIR / "rebalance_plan.json"
REVIEW_PATH = DATA_DIR / "risk_officer_review.json"
OVERRIDES_PATH = DATA_DIR / "risk_officer_overrides.jsonl"


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a literal 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def classify_orders(orders: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split rebalance_plan.json's orders into (vetoed, approved).

    An order is vetoed iff its riskGateWarnings or breakerWarnings list is
    non-empty — E2's existing warn-only signals, now enforced rather than
    merely displayed. No new numeric thresholds are introduced here.

    Args:
        orders: The "orders" list from rebalance_plan.json.

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
    rebalance_plan_path: Path = REBALANCE_PLAN_PATH,
    output_path: Path = REVIEW_PATH,
    save: bool = True,
) -> dict[str, Any]:
    """Load rebalance_plan.json, classify its orders, write risk_officer_review.json.

    Args:
        rebalance_plan_path: Path to rebalance_plan.json.
        output_path: Where to write risk_officer_review.json.
        save: If False, compute and return without writing the file (mirrors
            rebalancer.py's --no-save pattern).

    Returns:
        {"status": "ok"|"no_plan"|"plan_blocked", "generatedAt",
         "sourceRebalancePlanGeneratedAt", "vetoedOrders", "approvedOrders"}.
        "no_plan" (rebalance_plan_path doesn't exist) and "plan_blocked"
        (the plan's blockedReason is non-null) both return empty order
        lists and write no file — there is nothing to review yet.
    """
    if not Path(rebalance_plan_path).exists():
        return {"status": "no_plan", "vetoedOrders": [], "approvedOrders": []}

    plan = json.loads(Path(rebalance_plan_path).read_text())
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
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result, indent=2))
    return result


def log_risk_officer_override(
    ticker: str,
    action: str,
    account: str,
    shares: float | None,
    veto_reasons: list[str],
    rationale: str,
    overridden_by: str = "user",
    path: Path = OVERRIDES_PATH,
) -> None:
    """Append one accountability-trail record for a vetoed-order override.

    Called by risk-officer-agent.md — only a human decision to proceed with
    a vetoed order constitutes an "override." Mirrors thesis_breakers.py's
    log_breaker_override() exactly: append-only, one JSON object per line.

    Args:
        ticker: Order's ticker.
        action: "buy" or "sell".
        account: Order's account (e.g. "TFSA").
        shares: Order's share count, or None if unknown.
        veto_reasons: The order's vetoReasons at time of override.
        rationale: The user's stated reason for proceeding anyway.
        overridden_by: Who made the call — defaults to "user".
        path: Target JSONL file.
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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _cli_log_override(
    ticker: str,
    action: str,
    account: str,
    rationale: str,
    overridden_by: str = "user",
    review_path: Path = REVIEW_PATH,
    overrides_path: Path = OVERRIDES_PATH,
) -> None:
    """Resolve a vetoed order's shares/vetoReasons from risk_officer_review.json, then log.

    Thin wrapper so a caller (risk-officer-agent.md, via --log-override) only
    needs a ticker/action/account/rationale — not risk_officer_review.json's
    internal shape.

    Args:
        ticker: Order's ticker.
        action: "buy" or "sell".
        account: Order's account.
        rationale: The user's stated reason for proceeding anyway.
        overridden_by: Who made the call — defaults to "user".
        review_path: Path to risk_officer_review.json.
        overrides_path: Target JSONL file.

    Raises:
        ValueError: If review_path doesn't exist, or no vetoed order matches
            (ticker, action, account).
    """
    if not Path(review_path).exists():
        raise ValueError(f"{review_path} not found — run risk_officer.py --pretty first")
    review = json.loads(Path(review_path).read_text())
    match = next(
        (
            o for o in review.get("vetoedOrders", [])
            if o["ticker"] == ticker and o["action"] == action and o["account"] == account
        ),
        None,
    )
    if match is None:
        raise ValueError(f"no vetoed order found for {ticker}/{action}/{account} in {review_path}")
    log_risk_officer_override(
        ticker=ticker, action=action, account=account, shares=match.get("shares"),
        veto_reasons=match.get("vetoReasons", []), rationale=rationale,
        overridden_by=overridden_by, path=overrides_path,
    )


def main() -> None:
    """CLI entry point — compute the risk-officer review, or log an override.

    --log-override lets risk-officer-agent.md record a vetoed-order override
    without importing this module directly.
    """
    parser = argparse.ArgumentParser(description="Risk officer veto classification / override logging")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing risk_officer_review.json")
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
