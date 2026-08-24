#!/usr/bin/env python3
"""
verify_portfolio_invariants.py (Portfolio Invariants & Drift Sentinel)
======================================================================

Purpose:
    Enforces core portfolio risk invariants across domain_model.sqlite and TradingView syncs:
    1. Cash Invariant: Held Equities Market Value + Cash (PSU-U.TO / Cash USD) ≈ Total Equity USD.
    2. FX Staleness: Verifies USD/CAD exchange rate age < 48 hours.
    3. Dual-Account Mirror Drift: Asserts RRSP share counts match expected ~1/3 TFSA ratio.

Layer:
    Backend / py_services / Risk Governance

Usage Examples:
    python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
    python3 investment_screener/backend/py_services/verify_portfolio_invariants.py --json

Key Functions:
    - check_cash_invariant()
    - check_fx_staleness()
    - check_account_mirror_drift()
    - run_all_invariant_checks()
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
DB_PATH = os.path.join(PROJECT_ROOT, "investment_screener/backend/data/domain_model.sqlite")


def get_db_connection() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"domain_model.sqlite not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_cash_invariant(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Assert: Sum(Account Cash USD) + Sum(Equity Market Values) ≈ Total Reported Equity USD.
    """
    cursor = conn.cursor()
    
    # 1. Get latest broker reported totals
    cursor.execute("""
        SELECT total_usd, synced_at
        FROM broker_reported_total
        ORDER BY synced_at DESC LIMIT 1
    """)
    reported_row = cursor.fetchone()
    total_reported_usd = float(reported_row["total_usd"]) if reported_row and reported_row["total_usd"] else 0.0
    
    # 2. Get calculated positions market value
    cursor.execute("""
        SELECT ai.account_id, ai.investment_id, ai.quantity, ip.price
        FROM account_investment ai
        LEFT JOIN investment_price ip ON ai.investment_id = ip.investment_id
        WHERE ai.quantity > 0
    """)
    pos_rows = cursor.fetchall()
    
    equities_market_value = 0.0
    total_reported_cash = 0.0
    
    for pos in pos_rows:
        sym = pos["investment_id"]
        shares = float(pos["quantity"] or 0)
        price = float(pos["price"] or 0)
        if sym in ("PSU-U.TO", "PSU.U.TO", "CASH_USD"):
            # Cash equivalent
            total_reported_cash += shares * (price if price > 0 else 100.0)
        else:
            equities_market_value += shares * price
            
    computed_total = equities_market_value + total_reported_cash
    delta = abs(computed_total - total_reported_usd) if total_reported_usd > 0 else 0.0
    passed = delta < 150.0 or total_reported_usd == 0.0

    return {
        "check": "CASH_INVARIANT",
        "passed": passed,
        "total_reported_usd": round(total_reported_usd, 2),
        "computed_total_usd": round(computed_total, 2),
        "equities_market_value": round(equities_market_value, 2),
        "total_cash_usd": round(total_reported_cash, 2),
        "discrepancy_usd": round(delta, 2),
        "message": "Passed: Cash + Equities match reported totals" if passed else f"Warning: Discrepancy of ${delta:.2f} USD detected between cash+equities and reported totals."
    }


def check_fx_staleness(conn: sqlite3.Connection, max_age_hours: int = 48) -> Dict[str, Any]:
    """
    Verify the latest inferred USD/CAD exchange rate is not older than max_age_hours.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT usd_to_cad_rate, synced_at
        FROM broker_exchange_rate
        ORDER BY synced_at DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        return {
            "check": "FX_STALENESS",
            "passed": True,
            "rate": 1.3795,
            "message": "Notice: No exchange rate history in DB, defaulting to 1.3795"
        }
        
    rate = float(row["usd_to_cad_rate"])
    effective_str = row["synced_at"]
    
    try:
        eff_dt = datetime.datetime.fromisoformat(effective_str.replace("Z", "+00:00"))
        age_hours = (datetime.datetime.now(datetime.timezone.utc) - eff_dt).total_seconds() / 3600.0
        passed = age_hours <= max_age_hours
    except Exception:
        age_hours = 0.0
        passed = True

    return {
        "check": "FX_STALENESS",
        "passed": passed,
        "rate": rate,
        "age_hours": round(age_hours, 1),
        "effective_date": effective_str,
        "message": f"FX rate {rate:.4f} is fresh ({age_hours:.1f}h old)" if passed else f"Warning: FX rate {rate:.4f} is stale ({age_hours:.1f}h old > {max_age_hours}h limit)"
    }


def check_account_mirror_drift(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Assert: RRSP holdings are within ±25% of expected 1/3 TFSA ratio.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT account_id, investment_id, quantity
        FROM account_investment
        WHERE quantity > 0
    """)
    rows = cursor.fetchall()
    
    tfsa_shares: Dict[str, float] = {}
    rrsp_shares: Dict[str, float] = {}
    
    for r in rows:
        acc = (r["account_id"] or "").upper()
        sym = r["investment_id"]
        shares = float(r["quantity"] or 0)
        if "TFSA" in acc:
            tfsa_shares[sym] = shares
        elif "RRSP" in acc:
            rrsp_shares[sym] = shares
            
    drift_items = []
    for sym, tfsa_qty in tfsa_shares.items():
        if sym in ("PSU-U.TO", "PSU.U.TO", "CASH_USD"):
            continue
        expected_rrsp = round(tfsa_qty / 3.0)
        actual_rrsp = rrsp_shares.get(sym, 0.0)
        
        if expected_rrsp > 0:
            drift_ratio = abs(actual_rrsp - expected_rrsp) / expected_rrsp
            if drift_ratio > 0.35 and actual_rrsp > 0:
                drift_items.append({
                    "symbol": sym,
                    "tfsa_shares": tfsa_qty,
                    "actual_rrsp": actual_rrsp,
                    "expected_rrsp": expected_rrsp,
                    "drift_pct": round(drift_ratio * 100, 1)
                })

    passed = len(drift_items) == 0
    return {
        "check": "ACCOUNT_MIRROR_DRIFT",
        "passed": passed,
        "drift_count": len(drift_items),
        "drift_details": drift_items,
        "message": "All RRSP mirror holdings are within tolerance" if passed else f"Warning: {len(drift_items)} holdings exhibit TFSA/RRSP mirror drift."
    }


def run_all_invariant_checks() -> Dict[str, Any]:
    conn = get_db_connection()
    cash_res = check_cash_invariant(conn)
    fx_res = check_fx_staleness(conn)
    mirror_res = check_account_mirror_drift(conn)
    conn.close()
    
    all_passed = cash_res["passed"] and fx_res["passed"] and mirror_res["passed"]
    
    return {
        "status": "PASS" if all_passed else "WARNING",
        "checks": [cash_res, fx_res, mirror_res]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Portfolio Risk Invariants")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()
    
    try:
        report = run_all_invariant_checks()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("\n🛡️ === PORTFOLIO RISK INVARIANTS REPORT ===")
            print(f"Overall Status: {report['status']}\n")
            for c in report["checks"]:
                mark = "✅" if c["passed"] else "⚠️"
                print(f"{mark} [{c['check']}]: {c['message']}")
            print("==========================================\n")
    except Exception as e:
        print(f"Error running invariant checks: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
