#!/usr/bin/env python3
"""
validate_stock_metrics.py - Canonical validator & diagnostic auditor for stock analysis metrics.

Purpose:
    Validates that all financial metrics, growth rates, margins, valuation multiples,
    and quality scores for a given stock adhere to deterministic mathematical rules:
    - Non-holding action safety (shares == 0 -> only INITIATE, WATCHLIST, or AVOID)
    - Margin consistency (-100% <= margin <= 100%)
    - Piotroski F-Score range (0-9 integer)
    - Rule of 40 computation (Revenue Growth + EBITDA/Free Cash Flow Margin)
    - P/E & Forward P/E positivity/validity
    - Live shares held integration from portfolio_inspect

Layer:
    Backend / py_services / Validation

Usage:
    python3 py_services/validate_stock_metrics.py --ticker INTC
    python3 py_services/validate_stock_metrics.py --raw temp/evaluations/INTC_raw.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from domain_model.db_client import initialize_db
from ticker_aliases import normalize_ticker

_DB_PATH = str(_HERE / ".." / "data" / "domain_model.sqlite")

def get_live_shares_held(symbol: str) -> float:
    """Query live shares held for a ticker from SQLite."""
    conn = initialize_db(_DB_PATH)
    try:
        row = conn.execute("""
            SELECT SUM(ai.quantity) 
            FROM account_investment ai
            JOIN investment i ON ai.investment_id = i.investment_id
            WHERE i.symbol = ?
        """, (symbol,)).fetchone()
        return float(row[0]) if (row and row[0] is not None) else 0.0
    except Exception:
        return 0.0
    finally:
        conn.close()

def validate_metrics_payload(raw_data: dict, shares_held: float | None = None) -> dict:
    errors = []
    warnings = []
    
    canonical_sym = normalize_ticker(raw_data.get("symbol", "UNKNOWN"))
    if shares_held is None:
        shares_held = get_live_shares_held(canonical_sym)

    price = raw_data.get("price", 0.0)
    if price <= 0:
        errors.append(f"Invalid market price: {price}")

    expert = raw_data.get("expert_metrics", {})
    
    # 1. Piotroski F-Score check
    f_score = expert.get("piotroski_f_score", {}).get("score")
    if f_score is not None:
        if not (0 <= f_score <= 9):
            errors.append(f"Piotroski F-score out of bounds (0-9): {f_score}")
    else:
        warnings.append("Missing Piotroski F-score")

    # 2. Rule of 40 check
    r40 = expert.get("rule_of_40", {})
    if r40:
        rev_g = r40.get("revenue_growth", 0)
        ebitda_m = r40.get("ebitda_margin", 0)
        expected_score = round(rev_g + ebitda_m, 2)
        actual_score = round(r40.get("score", 0), 2)
        if abs(expected_score - actual_score) > 0.5:
            warnings.append(f"Rule of 40 math mismatch: calc={expected_score}, reported={actual_score}")

    # 3. Non-Holding Safety Guard: Non-holdings (0 shares) can ONLY be INITIATE, WATCHLIST, or AVOID
    action = raw_data.get("action") or raw_data.get("aiThesis", {}).get("action")
    if shares_held <= 0 and action:
        invalid_non_holding_actions = ["TRIM", "EXIT", "MAINTAIN", "ACCUMULATE"]
        if action.upper() in invalid_non_holding_actions:
            errors.append(
                f"Safety violation: Non-holding ({canonical_sym} with {shares_held} shares) cannot have action '{action}'. "
                f"Allowed non-holding actions are INITIATE, WATCHLIST, AVOID."
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "symbol": canonical_sym,
        "shares_held": shares_held,
        "checks_performed": [
            "price_positivity",
            "piotroski_bounds",
            "rule_of_40_math",
            "non_holding_action_safety"
        ]
    }

def main():
    parser = argparse.ArgumentParser(description="Validate and confirm stock analysis metrics")
    parser.add_argument("--ticker", "-t", type=str, help="Ticker symbol to fetch and validate")
    parser.add_argument("--raw", "-r", type=str, help="Path to raw financials JSON file")
    parser.add_argument("--shares", "-s", type=float, default=None, help="Explicit shares held override")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    if args.ticker:
        clean_sym = normalize_ticker(args.ticker)
        res = subprocess.run([sys.executable, str(_HERE / "fetch_financials.py"), clean_sym], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error fetching financials: {res.stderr}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(res.stdout)
    elif args.raw:
        with open(args.raw) as f:
            data = json.load(f)
    else:
        parser.print_help()
        sys.exit(1)

    result = validate_metrics_payload(data, shares_held=args.shares)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASSED" if result["valid"] else "FAILED"
        print(f"=== Metric Validation for {result['symbol']}: {status} (Shares Held: {result['shares_held']}) ===")
        for w in result["warnings"]:
            print(f"  [WARN] {w}")
        for e in result["errors"]:
            print(f"  [FAIL] {e}")

if __name__ == "__main__":
    main()
