#!/usr/bin/env python3
"""
execution_quality_scorecard.py - Python utility script.

Purpose:
    Phase 6 execution-quality groundwork. Reads Phase 5E-8's
    orders_executed.jsonl audit trail (logged by order_risk_gates.py's
    log_order_execution(), never read by any script until now) and
    computes a decision breakdown, per-gate fail rate, and an
    overridden-order worklist. Deterministic — no ML, no return/P&L
    correlation (that needs price-history joining out of scope here).

Layer:
    Backend / Python Services

Usage:
    python3 execution_quality_scorecard.py [--json]

Key Functions (Index):
    - load_orders_executed()
    - compute_decision_breakdown()
    - compute_gate_fail_rates()
    - compute_overridden_registry()
    - build_report()
    - main()

Key Input Dependencies:
    - investment_screener/backend/data/orders_executed.jsonl (gitignored, may not exist yet)

Key Output Dependencies:
    None
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ORDERS_EXECUTED_PATH = DATA_DIR / "orders_executed.jsonl"

_DECISIONS = ("EXECUTED", "BLOCKED", "OVERRIDDEN")


def load_orders_executed(path: Path = ORDERS_EXECUTED_PATH) -> list[dict[str, Any]]:
    """Load orders_executed.jsonl. Missing file degrades to an empty list, never raises."""
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def compute_decision_breakdown(orders: list[dict[str, Any]]) -> dict[str, int]:
    """Count logged order attempts by decision (EXECUTED/BLOCKED/OVERRIDDEN)."""
    counts = {d: 0 for d in _DECISIONS}
    for order in orders:
        decision = order.get("decision")
        if decision in counts:
            counts[decision] += 1
    return counts


def compute_gate_fail_rates(orders: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-gate fail rate across every logged attempt that included that gate.

    A gate never seen in any record is absent from the result, not reported as 0% fail
    (0% fail and "never evaluated" are different facts).
    """
    seen: dict[str, dict[str, int]] = {}
    for order in orders:
        for gate in order.get("gate_result", {}).get("gates", []):
            name = gate["name"]
            bucket = seen.setdefault(name, {"failCount": 0, "totalSeen": 0})
            bucket["totalSeen"] += 1
            if not gate["passed"]:
                bucket["failCount"] += 1
    return {
        name: {**stats, "failRate": round(stats["failCount"] / stats["totalSeen"], 4)}
        for name, stats in seen.items()
    }


def compute_overridden_registry(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flat worklist of every OVERRIDDEN order: ticker, which gate(s) it overrode, reasons.

    Manual-review worklist, not an automated verdict — no outcome/return computation.
    """
    registry = []
    for order in orders:
        if order.get("decision") != "OVERRIDDEN":
            continue
        gates = order.get("gate_result", {}).get("gates", [])
        failed_gates = [g["name"] for g in gates if not g["passed"]]
        reasons = [g["reason"] for g in gates if not g["passed"]]
        registry.append({
            "ticker": order.get("order", {}).get("ticker"),
            "side": order.get("order", {}).get("side"),
            "timestamp": order.get("timestamp"),
            "overriddenGates": failed_gates,
            "reasons": reasons,
        })
    return registry


def build_report(orders_path: Path = ORDERS_EXECUTED_PATH) -> dict[str, Any]:
    """Build the full execution-quality scorecard dict."""
    orders = load_orders_executed(orders_path)
    return {
        "totalOrdersLogged": len(orders),
        "decisionBreakdown": compute_decision_breakdown(orders),
        "gateFailRates": compute_gate_fail_rates(orders),
        "overriddenRegistry": compute_overridden_registry(orders),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Phase 6 execution-quality scorecard")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"Execution quality — {report['totalOrdersLogged']} order attempt(s) logged")
    if report["totalOrdersLogged"] == 0:
        print("  No orders_executed.jsonl data yet — this is expected early on, not a bug.")
        return
    breakdown = report["decisionBreakdown"]
    print(f"  Decisions: {breakdown['EXECUTED']} executed / {breakdown['BLOCKED']} blocked / "
          f"{breakdown['OVERRIDDEN']} overridden")
    for gate, stats in report["gateFailRates"].items():
        print(f"  Gate {gate:<18} fail rate {stats['failRate']:.0%} "
              f"({stats['failCount']}/{stats['totalSeen']})")
    if report["overriddenRegistry"]:
        print("  Overridden orders (manual review worklist):")
        for entry in report["overriddenRegistry"]:
            print(f"    {entry['ticker']} {entry['side']} — overrode {entry['overriddenGates']}: "
                  f"{'; '.join(entry['reasons'])}")


if __name__ == "__main__":
    main()
