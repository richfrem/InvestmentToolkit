#!/usr/bin/env python3
"""
validate_projection.py — stock-valuation plugin

Pre-persistence validation script for Projection JSON objects.
Catches schema violations before they reach the backend API,
giving the agent deterministic error messages to self-correct.

Usage:
    python3 validate_projection.py < /tmp/{TICKER}_projection.json
    echo $?   # 0 = valid, 1 = validation errors

Options:
    --help      Show this help message
    --verbose   Print field-by-field results
"""

import json
import sys
import argparse
from typing import Any


ACCUMULATE_SPREAD_THRESHOLD_PCT = 25.0
ACCUMULATE_DCF_UPSIDE_THRESHOLD_PCT = 15.0


def check_accumulate_gate(projection: dict) -> dict:
    """Gate check: ACCUMULATE requires >=2 of 3 valuation lenses agreeing.

    Lenses: (1) DCF upside > 15% (analyticsLog.dcf.upsidePct), (2) comps
    implied price (midpoint of analyticsLog.comps.impliedPriceRange) >
    current price, (3) implied growth < base-case growth
    (analyticsLog.reverseDcf.impliedGrowthVsBaseCase < 0 — the market is
    pricing in less optimism than our own base case, a margin-of-safety
    signal). A projection whose aiThesis.action isn't ACCUMULATE always
    passes trivially — this gate only constrains that one action.

    Args:
        projection: Full projection dict (aiThesis, snapshot, analyticsLog).

    Returns:
        {"gatePassed": bool, "lensesAgreeing": int,
         "lensResults": {"dcf": bool, "comps": bool, "impliedGrowth": bool},
         "spreadPct": float, "disagreementNoteRequired": bool}
    """
    analytics = projection.get("analyticsLog", {}) or {}
    action = projection.get("aiThesis", {}).get("action")
    current_price = projection.get("snapshot", {}).get("price")

    dcf_upside_pct = analytics.get("dcf", {}).get("upsidePct")
    dcf_lens = bool(dcf_upside_pct is not None and dcf_upside_pct > ACCUMULATE_DCF_UPSIDE_THRESHOLD_PCT)

    comps = analytics.get("comps", {}) or {}
    comps_price = None
    if comps.get("status") == "ok" and current_price:
        implied_range = comps.get("impliedPriceRange", {})
        comps_price = (implied_range.get("low", 0) + implied_range.get("high", 0)) / 2
    comps_lens = bool(comps_price is not None and current_price and comps_price > current_price)

    reverse_dcf = analytics.get("reverseDcf", {}) or {}
    implied_growth_vs_base = reverse_dcf.get("impliedGrowthVsBaseCase")
    implied_growth_lens = bool(implied_growth_vs_base is not None and implied_growth_vs_base < 0)

    lenses_agreeing = sum([dcf_lens, comps_lens, implied_growth_lens])
    gate_passed = (action != "ACCUMULATE") or (lenses_agreeing >= 2)

    prices = [p for p in [analytics.get("dcf", {}).get("weightedFairValue"), comps_price] if p is not None]
    spread_pct = 0.0
    if len(prices) >= 2 and min(prices) > 0:
        spread_pct = round((max(prices) - min(prices)) / min(prices) * 100, 2)

    return {
        "gatePassed": gate_passed,
        "lensesAgreeing": lenses_agreeing,
        "lensResults": {"dcf": dcf_lens, "comps": comps_lens, "impliedGrowth": implied_growth_lens},
        "spreadPct": spread_pct,
        "disagreementNoteRequired": spread_pct > ACCUMULATE_SPREAD_THRESHOLD_PCT,
    }


def check(condition: bool, field: str, message: str, errors: list[str]) -> None:
    """Append an error message if condition is False."""
    if not condition:
        errors.append(f"[FAIL] {field}: {message}")


def validate_projection(data: dict[str, Any], verbose: bool = False) -> list[str]:
    """
    Validate a Projection JSON object against the stock-valuation schema.

    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []

    # --- Top-level required fields ---
    for field in ["ticker", "id", "source", "schemaVersion", "version", "savedAt",
                  "rationale", "snapshot", "scenarios", "aiThesis", "globalSettings"]:
        check(field in data, field, f"Required field '{field}' is missing", errors)

    # --- Scenarios ---
    scenarios = data.get("scenarios", {})
    for case in ["bear", "base", "bull"]:
        check(case in scenarios, f"scenarios.{case}", f"Scenario '{case}' is missing", errors)

    bear = scenarios.get("bear", {})
    base = scenarios.get("base", {})
    bull = scenarios.get("bull", {})

    # Weight sum
    try:
        weight_sum = float(bear.get("weight", 0)) + float(base.get("weight", 0)) + float(bull.get("weight", 0))
        check(0.99 <= weight_sum <= 1.01, "weights",
              f"Weights sum to {weight_sum:.4f}; must be 1.0 ±0.01", errors)
    except (TypeError, ValueError):
        errors.append("[FAIL] weights: One or more weights is not a valid number")

    # Growth ordering
    try:
        check(float(bear.get("growthRate", 0)) < float(base.get("growthRate", 0)),
              "growthRate", "bear.growthRate must be < base.growthRate", errors)
        check(float(base.get("growthRate", 0)) < float(bull.get("growthRate", 0)),
              "growthRate", "base.growthRate must be < bull.growthRate", errors)
    except (TypeError, ValueError):
        errors.append("[FAIL] growthRate: Non-numeric growth rate detected")

    # Price ordering
    try:
        check(float(bear.get("scenarioPrice", 0)) < float(base.get("scenarioPrice", 0)),
              "scenarioPrice", "bear.scenarioPrice must be < base.scenarioPrice", errors)
        check(float(base.get("scenarioPrice", 0)) < float(bull.get("scenarioPrice", 0)),
              "scenarioPrice", "base.scenarioPrice must be < bull.scenarioPrice", errors)
    except (TypeError, ValueError):
        errors.append("[FAIL] scenarioPrice: Non-numeric scenario price detected")

    # --- Hard schema limits per scenario ---
    limits = {
        "growthRate": (-100, 1000),
        "netMargin": (-100, 100),
        "exitPE": (0, 1000),
        "qualityMultiplier": (0.1, 10.0),
        "moatScore": (0, 5),
        "managementScore": (0, 5),
        "shareChange": (-100, 1000),
    }
    for case_name, case_data in [("bear", bear), ("base", base), ("bull", bull)]:
        for field, (lo, hi) in limits.items():
            val = case_data.get(field)
            if val is not None:
                try:
                    check(lo <= float(val) <= hi, f"scenarios.{case_name}.{field}",
                          f"Value {val} out of range [{lo}, {hi}]", errors)
                except (TypeError, ValueError):
                    errors.append(f"[FAIL] scenarios.{case_name}.{field}: Must be a number, got '{val}'")

    # --- Confidence score ---
    confidence = data.get("aiThesis", {}).get("confidenceScore") or data.get("confidenceScore")
    if confidence is not None:
        try:
            check(0.0 <= float(confidence) <= 1.0, "confidenceScore",
                  f"Must be in [0.0, 1.0], got {confidence}", errors)
        except (TypeError, ValueError):
            errors.append(f"[FAIL] confidenceScore: Must be a number, got '{confidence}'")

    # --- Valuation-committee gate (Phase 2a) ---
    gate = check_accumulate_gate(data)
    if not gate["gatePassed"]:
        errors.append(
            f"[FAIL] aiThesis.action: ACCUMULATE requires >=2 of 3 valuation lenses "
            f"agreeing, only {gate['lensesAgreeing']} do ({gate['lensResults']})"
        )
    if gate["disagreementNoteRequired"]:
        print(
            f"[WARN] valuation lenses disagree by {gate['spreadPct']}% (>25%) — "
            "document this disagreement in rationale before finalizing.",
            file=sys.stderr,
        )

    if verbose:
        if errors:
            print(f"Validation FAILED — {len(errors)} error(s):")
            for e in errors:
                print(f"  {e}")
        else:
            print("Validation PASSED — projection is schema-compliant.")

    return errors


def main() -> None:
    """Entry point: read JSON from stdin, validate, exit with appropriate code."""
    parser = argparse.ArgumentParser(
        description="Validate a stock-valuation Projection JSON before persistence.")
    parser.add_argument("--verbose", action="store_true", help="Print field-by-field results")
    args = parser.parse_args()

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"[FAIL] Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_projection(data, verbose=True)

    if args.verbose and not errors:
        print("All checks passed.")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
