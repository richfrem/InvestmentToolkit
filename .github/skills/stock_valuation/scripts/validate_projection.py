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
