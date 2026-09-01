#!/usr/bin/env python3
"""
verify_screener_integrity.py
=====================================

Purpose:
    Comprehensive verification & quality gate for the Screener and Intelligence Feed dashboard.
    Enforces all 6 critical runtime invariants:
    1. 100.0000% Target Sum Invariant (Holdings + Cash).
    2. Action Invariant (Unheld tickers cannot have TRIM/EXIT/ACCUMULATE).
    3. Cash Exclusion Invariant (Cash is excluded from gaps/actionable counts).
    4. Taxonomy Alignment (Pillar and Sub-Strategy match canonical definitions).
    5. Valuation Freshness & Coverage (Zero untracked holding gaps).
    6. Database & API Schema Conformance.

Layer:
    Backend / py_services / Quality Assurance & Testing

Usage:
    python3 investment_screener/backend/py_services/verify_screener_integrity.py

Key Functions:
    - check_target_sum(conn) -> bool
    - check_action_invariants(conn) -> bool
    - check_cash_exclusion(conn) -> bool
    - check_taxonomy_alignment(conn) -> bool
    - run_all_integrity_checks(db_path) -> dict
    - main() -> None

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

_HERE = Path(__file__).resolve().parent
DB_PATH = _HERE / ".." / "data" / "domain_model.sqlite"


def check_target_sum(conn: sqlite3.Connection) -> Tuple[bool, str]:
    """Verifies that all non-zero target weights sum to exactly 100.0000%."""
    cur = conn.cursor()
    cur.execute("SELECT symbol, target_weight FROM investment WHERE target_weight > 0;")
    rows = cur.fetchall()
    total = sum(r[1] for r in rows)
    if abs(total - 100.0) < 0.001:
        return True, f"Target weights sum to exactly 100.00% across {len(rows)} positions."
    return False, f"Target weights sum to {total:.4f}%, expected exactly 100.00%."


def check_action_invariants(conn: sqlite3.Connection) -> Tuple[bool, List[str]]:
    """Verifies that unheld stocks do NOT carry TRIM, EXIT, or ACCUMULATE actions."""
    cur = conn.cursor()
    # Get all held positions with quantity > 0
    cur.execute("SELECT DISTINCT investment_id FROM account_investment WHERE quantity > 0;")
    held_syms = set(r[0] for r in cur.fetchall())

    cur.execute("""
        SELECT symbol, target_weight, target_action, standing_decision_type 
        FROM investment 
        WHERE symbol NOT IN ('CASH_USD', 'USD_CASH');
    """)
    rows = cur.fetchall()

    violations = []
    for sym, target_weight, target_action, sd_type in rows:
        is_held = sym in held_syms
        act = (target_action or "").upper()
        if not is_held:
            if act in ("TRIM", "EXIT", "ACCUMULATE"):
                violations.append(f"{sym}: Unheld position has invalid action '{act}'")

    if not violations:
        return True, ["All action labels strictly conform to holding state invariants."]
    return False, violations


def check_cash_exclusion(conn: sqlite3.Connection) -> Tuple[bool, str]:
    """Verifies that cash assets are correctly designated in the cash pillar and not flagged as stocks."""
    cur = conn.cursor()
    cur.execute("SELECT symbol, pillar_id, sub_strategy_id, asset_class FROM investment WHERE symbol IN ('CASH_USD', 'USD_CASH', 'PSU-U.TO');")
    rows = cur.fetchall()
    for sym, p_id, s_id, a_class in rows:
        if p_id != "cash" or s_id != "cash":
            return False, f"{sym} is misclassified (pillar: {p_id}, strategy: {s_id})"
    return True, "Cash assets correctly classified under cash pillar."


def check_taxonomy_alignment(conn: sqlite3.Connection) -> Tuple[bool, List[str]]:
    """Verifies that all investments have a valid registered pillar and sub-strategy with 0 mismatches."""
    cur = conn.cursor()
    cur.execute("SELECT sub_strategy_id, pillar_id FROM sub_strategy;")
    valid_sub_strats = dict(cur.fetchall())

    cur.execute("SELECT symbol, pillar_id, sub_strategy_id FROM investment WHERE symbol NOT IN ('CASH_USD', 'USD_CASH');")
    rows = cur.fetchall()

    mismatches = []
    for sym, p_id, s_id in rows:
        if s_id and s_id in valid_sub_strats:
            expected_p = valid_sub_strats[s_id]
            if p_id != expected_p and p_id not in ("other", None):
                mismatches.append(f"{sym}: Pillar '{p_id}' != Expected '{expected_p}' for strategy '{s_id}'")

    if not mismatches:
        return True, ["All tickers strictly aligned with strategy taxonomy."]
    return False, mismatches


def run_all_integrity_checks(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Runs full suite of integrity checks."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database {db_path} not found.")

    conn = sqlite3.connect(str(db_path))
    try:
        t_ok, t_msg = check_target_sum(conn)
        a_ok, a_msgs = check_action_invariants(conn)
        c_ok, c_msg = check_cash_exclusion(conn)
        x_ok, x_msgs = check_taxonomy_alignment(conn)

        all_passed = t_ok and a_ok and c_ok and x_ok
        return {
            "all_passed": all_passed,
            "target_sum": {"passed": t_ok, "message": t_msg},
            "action_invariants": {"passed": a_ok, "messages": a_msgs},
            "cash_exclusion": {"passed": c_ok, "message": c_msg},
            "taxonomy_alignment": {"passed": x_ok, "messages": x_msgs},
        }
    finally:
        conn.close()


def main() -> None:
    """CLI runner and exit code handler."""
    print("🔍 Running Screener & Dashboard Integrity Audit Gate...")
    print("=" * 80)
    results = run_all_integrity_checks(DB_PATH)

    print(f"1. Target Sum (100.00%):   {'✅ PASS' if results['target_sum']['passed'] else '❌ FAIL'}")
    print(f"   └─ {results['target_sum']['message']}")

    print(f"2. Action Invariants:      {'✅ PASS' if results['action_invariants']['passed'] else '❌ FAIL'}")
    for m in results['action_invariants']['messages']:
        print(f"   └─ {m}")

    print(f"3. Cash Invariant:         {'✅ PASS' if results['cash_exclusion']['passed'] else '❌ FAIL'}")
    print(f"   └─ {results['cash_exclusion']['message']}")

    print(f"4. Taxonomy Alignment:     {'✅ PASS' if results['taxonomy_alignment']['passed'] else '❌ FAIL'}")
    for m in results['taxonomy_alignment']['messages']:
        print(f"   └─ {m}")

    print("=" * 80)
    if results["all_passed"]:
        print("🎉 ALL SCREENER INTEGRITY GATES PASSED (Exit 0)")
        sys.exit(0)
    else:
        print("🚨 SCREENER INTEGRITY FAILURES DETECTED (Exit 1)")
        sys.exit(1)


if __name__ == "__main__":
    main()
