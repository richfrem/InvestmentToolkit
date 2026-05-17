#!/usr/bin/env python3
"""
tv_test_harness.py — TradingView CDP prerequisite and DOM selector smoke checks.

Section 0  — Prerequisites: TV reachable, broker connected, account readable, buying power > 0
Section 0.5 — DOM Selector Smoke: critical selectors that all CDP automation depends on.
              ANY missing selector aborts the suite immediately — a missing selector means
              all form-fill tests would fail with cryptic errors, not useful diagnostics.

TV ships DOM updates 2-4 times/year; Section 0.5 catches regressions before they hide
in cryptic automation failures downstream.

Usage:
    python3 plugins/tradingview/tests/tv_test_harness.py --suite prereqs
    python3 plugins/tradingview/tests/tv_test_harness.py --suite selectors
    python3 plugins/tradingview/tests/tv_test_harness.py           # runs both sections

Exit codes:
    0  — all checks passed
    1  — prerequisite failure (TV unreachable, no broker, etc.)
    2  — DOM selector missing (CRITICAL — suite aborted)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TV_NODE_DIR = REPO_ROOT / "plugins/tradingview/node"

OK = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
CRITICAL = "\033[91m[CRITICAL]\033[0m"
HEADER = "\033[1m"
RESET = "\033[0m"


def _run_node(js: str, timeout: int = 10) -> dict:
    """Execute inline Node.js ES module in the tradingview/node context."""
    r = subprocess.run(
        ["node", "--input-type=module"],
        input=js, capture_output=True, text=True,
        timeout=timeout, cwd=str(TV_NODE_DIR),
    )
    stdout = r.stdout.strip()
    if not stdout:
        raise RuntimeError(r.stderr.strip()[:500] or "No output from Node.js")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Non-JSON output: {stdout[:200]}")


# ── Section 0: Prerequisites ──────────────────────────────────────────────────

def check_tv_reachable() -> tuple[bool, str]:
    """[0.1] TV reachable (port 9222) — CDP connect."""
    try:
        result = _run_node("""
import { connect } from './connection.js';
try {
    await connect();
    process.stdout.write(JSON.stringify({ ok: true }) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ ok: false, error: e.message }) + '\\n');
    process.exit(1);
}
""")
        if result.get("ok"):
            return True, "CDP connection established"
        return False, f"CDP connect failed: {result.get('error', 'unknown')}"
    except Exception as e:
        return False, f"CDP connect error: {e}"


def check_broker_connected() -> tuple[bool, str]:
    """[0.2] Broker connected — account name visible in broker panel."""
    try:
        result = _run_node("""
import { inspectBrokerPanel } from './core/broker_data.js';
try {
    const info = await inspectBrokerPanel();
    process.stdout.write(JSON.stringify(info) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
""")
        if result.get("error"):
            return False, f"Broker panel inspect failed: {result['error']}"
        account = result.get("activeAccount")
        tabs = result.get("tabs", [])
        if account:
            return True, f"Broker active account: {account} ({len(tabs)} tabs visible)"
        # Tabs visible but no active account label — broker may be disconnected
        if tabs:
            return False, f"Broker panel has tabs but no active account — broker may be disconnected"
        return False, "Broker panel not found (no tabs, no account)"
    except Exception as e:
        return False, f"Broker check error: {e}"


def check_account_readable() -> tuple[bool, str]:
    """[0.3] Account readable — active account name visible."""
    try:
        result = _run_node("""
import { activeAccount } from './core/broker_data.js';
try {
    const acct = await activeAccount();
    process.stdout.write(JSON.stringify(acct) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
""", timeout=10)
        if result.get("error"):
            return False, f"Account read failed: {result['error']}"
        name = result.get("name") or result.get("accountType") or result.get("id") or str(result)
        if name and name != "{}":
            return True, f"Active account: {name}"
        return False, f"Could not read active account: {result}"
    except Exception as e:
        return False, f"Account read error: {e}"


def check_buying_power() -> tuple[bool, str]:
    """[0.4] Buying power > 0 — reads Account Summary tab."""
    try:
        result = _run_node("""
import { getBalances } from './core/broker_data.js';
try {
    const balances = await getBalances();
    process.stdout.write(JSON.stringify(balances) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
""", timeout=15)
        if result.get("error"):
            return False, f"Balance read failed: {result['error']}"
        # Accept any positive buying power in CAD or USD
        bp_cad = result.get("buyingPowerCAD") or 0
        bp_usd = result.get("buyingPowerUSD") or 0
        total_bp = result.get("totalBPCAD") or result.get("totalBPUSD") or 0
        best = max(bp_cad, bp_usd, total_bp)
        if best > 0:
            return True, f"Buying power: CAD={bp_cad}, USD={bp_usd}"
        return False, f"Buying power is 0 or missing. Balances: {list(result.keys())}"
    except Exception as e:
        return False, f"Buying power error: {e}"


# ── Section 0.5: DOM Selector Smoke ──────────────────────────────────────────

# Selectors that all CDP order automation depends on.
# Confirmed against TradingView Desktop DOM (2026-05-15, broker_data.js comments).
DOM_SELECTORS = [
    ('[class*="buyButton"]',      "Buy overlay button"),
    ('[class*="sellButton"]',     "Sell overlay button"),
    ('[class*="dropdownButton"]', "Account dropdown"),
    ('[class*="brokerBlock"]',    "Broker panel"),
]


def check_dom_selectors() -> tuple[bool, list[tuple[str, str, bool]]]:
    """[0.5] Check all critical DOM selectors exist.
    Returns (all_ok, list of (selector, description, found))."""
    selector_list = [s for s, _ in DOM_SELECTORS]
    selector_json = json.dumps(selector_list)
    try:
        result = _run_node(f"""
import {{ evaluate }} from './connection.js';
const selectors = {selector_json};
const results = await evaluate(`(function() {{
    var selectors = ${{JSON.stringify(selectors)}};
    return JSON.stringify(selectors.map(function(sel) {{
        var el = document.querySelector(sel);
        return {{ selector: sel, found: !!el }};
    }}));
}})()`).then(JSON.parse);
process.stdout.write(JSON.stringify(results) + '\\n');
process.exit(0);
""", timeout=15)
        if not isinstance(result, list):
            return False, [(s, d, False) for s, d in DOM_SELECTORS]

        found_map = {r["selector"]: r.get("found", False) for r in result}
        items = [(s, d, found_map.get(s, False)) for s, d in DOM_SELECTORS]
        all_ok = all(found for _, _, found in items)
        return all_ok, items
    except Exception:
        return False, [(s, d, False) for s, d in DOM_SELECTORS]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_section_0() -> bool:
    print(f"\n{HEADER}Section 0 — Prerequisites{RESET}")
    checks = [
        ("0.1", "TV reachable (port 9222)",      check_tv_reachable),
        ("0.2", "Broker connected",               check_broker_connected),
        ("0.3", "Account readable (TFSA/RRSP)",   check_account_readable),
        ("0.4", "Buying power > 0",               check_buying_power),
    ]
    all_ok = True
    for num, label, fn in checks:
        try:
            ok, msg = fn()
        except Exception as e:
            ok, msg = False, str(e)
        icon = OK if ok else FAIL
        print(f"  [{num}] {icon} {label}")
        print(f"       {msg}")
        if not ok:
            all_ok = False
    return all_ok


def run_section_05() -> bool:
    print(f"\n{HEADER}Section 0.5 — DOM Selector Smoke (CRITICAL){RESET}")
    all_ok, items = check_dom_selectors()

    for sel, desc, found in items:
        icon = OK if found else FAIL
        print(f"  {icon} [{desc}]  {sel}")

    if not all_ok:
        missing = [sel for sel, _, found in items if not found]
        print(f"\n{CRITICAL} {len(missing)} selector(s) missing — suite ABORTED:")
        for sel in missing:
            print(f"    {sel}")
        print("\n  TV ships DOM updates 2-4x/year. Update selectors in:")
        print("  plugins/tradingview/node/core/broker_data.js")
        print("  plugins/tradingview/node/core/trading.js")
        return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="TradingView CDP prerequisite checks")
    parser.add_argument(
        "--suite",
        choices=["prereqs", "selectors", "all"],
        default="all",
        help="Which section to run (default: all)",
    )
    args = parser.parse_args()

    print(f"\n{HEADER}=== TradingView Test Harness ==={RESET}")

    if args.suite in ("prereqs", "all"):
        ok0 = run_section_0()
        if not ok0:
            print(f"\n{FAIL} Section 0 failed — check TradingView and broker connection.")
            sys.exit(1)

    if args.suite in ("selectors", "all"):
        ok05 = run_section_05()
        if not ok05:
            print(f"\n{CRITICAL} Section 0.5 failed — DOM selectors broken, suite aborted.")
            sys.exit(2)

    print(f"\n{OK} All prerequisite checks passed.")


if __name__ == "__main__":
    main()
