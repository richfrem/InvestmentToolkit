#!/usr/bin/env python3
"""
validate_etf_analysis.py — etf-analysis plugin

Pre-persistence validator for ETF Analysis JSON objects.
Catches schema violations before files are written.

Usage:
    python3 validate_etf_analysis.py < /tmp/DXYZ_etf.json
    cat /tmp/KOID_etf.json | python3 validate_etf_analysis.py --verbose
    echo $?  # 0 = valid, 1 = errors
"""

import json
import sys
import argparse
from typing import Any


def check(condition: bool, field: str, message: str, errors: list) -> None:
    if not condition:
        errors.append(f"[FAIL] {field}: {message}")


def validate(data: dict[str, Any], verbose: bool = False) -> list[str]:
    errors = []

    # Top-level required fields
    for field in ["ticker", "id", "source", "schemaVersion", "schemaType",
                  "fundType", "version", "savedAt", "rationale", "snapshot",
                  "action", "actionRationale", "risks"]:
        check(field in data, field, f"Required field '{field}' is missing", errors)

    check(data.get("schemaType") == "ETF_ANALYSIS", "schemaType",
          f"Must be 'ETF_ANALYSIS', got '{data.get('schemaType')}'", errors)

    valid_types = {"CLOSED_END", "THEMATIC_ETF", "CASH_FUND"}
    check(data.get("fundType") in valid_types, "fundType",
          f"Must be one of {valid_types}, got '{data.get('fundType')}'", errors)

    valid_actions = {"BUY", "ACCUMULATE", "HOLD", "TRIM", "AVOID", "INITIATE"}
    check(data.get("action") in valid_actions, "action",
          f"Must be one of {valid_actions}, got '{data.get('action')}'", errors)

    snap = data.get("snapshot", {})
    check("price" in snap, "snapshot.price", "Current market price required", errors)
    check("currency" in snap, "snapshot.currency", "Currency required", errors)

    fund_type = data.get("fundType")

    if fund_type == "CLOSED_END":
        nav = data.get("navAnalysis", {})
        check("navAnalysis" in data, "navAnalysis",
              "CLOSED_END funds require navAnalysis block", errors)
        check("premiumPct" in nav, "navAnalysis.premiumPct",
              "premiumPct required for closed-end funds", errors)
        check("premiumRisk" in nav, "navAnalysis.premiumRisk",
              "premiumRisk (HIGH|MODERATE|LOW) required", errors)

    if fund_type == "THEMATIC_ETF":
        check("holdingsAnalysis" in data, "holdingsAnalysis",
              "THEMATIC_ETF funds require holdingsAnalysis block", errors)
        ha = data.get("holdingsAnalysis", {})
        check("topHoldings" in ha, "holdingsAnalysis.topHoldings",
              "topHoldings array required", errors)
        check("thesisAlignmentScore" in ha, "holdingsAnalysis.thesisAlignmentScore",
              "thesisAlignmentScore (0-100) required", errors)

    if verbose:
        if errors:
            for e in errors:
                print(e)
        else:
            print("[PASS] All validation checks passed")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"[FAIL] JSON parse error: {e}")
        sys.exit(1)

    errors = validate(data, verbose=args.verbose)
    if errors:
        if not args.verbose:
            for e in errors:
                print(e)
        sys.exit(1)
    else:
        if not args.verbose:
            print("[PASS] Valid ETF analysis JSON")
        sys.exit(0)


if __name__ == "__main__":
    main()
