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
