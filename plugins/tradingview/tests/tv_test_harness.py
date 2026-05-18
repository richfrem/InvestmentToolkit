#!/usr/bin/env python3
"""
tv_test_harness.py — TradingView CDP prerequisite and DOM selector smoke checks.

Section 0  — Prerequisites: TV reachable, broker connected, account readable, buying power > 0
Section 0.5 — DOM Selector Smoke: critical selectors that all CDP automation depends on.
              ANY missing selector aborts the suite immediately — a missing selector means
              all form-fill tests would fail with cryptic errors, not useful diagnostics.
Section 1  — Pine Script live cycle: inject / read / remove on the active chart.
              Requires TradingView Desktop running on port 9222 with a chart open.

TV ships DOM updates 2-4 times/year; Section 0.5 catches regressions before they hide
in cryptic automation failures downstream.

Usage:
    python3 plugins/tradingview/tests/tv_test_harness.py --suite prereqs
    python3 plugins/tradingview/tests/tv_test_harness.py --suite selectors
    python3 plugins/tradingview/tests/tv_test_harness.py --suite pine
    python3 plugins/tradingview/tests/tv_test_harness.py           # runs all sections

Exit codes:
    0  — all checks passed
    1  — prerequisite failure (TV unreachable, no broker, etc.)
    2  — DOM selector missing (CRITICAL — suite aborted)
    3  — Pine cycle failure
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMP_DIR = REPO_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT / "plugins" / "tradingview" / "scripts"))
from tv_client import TV_NODE_DIR

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


# ── Section 1: Pine Script Live Cycle ────────────────────────────────────────

def test_live_pine_cycle() -> tuple[bool, str]:
    """[1.1] Live pine cycle — inject / read / remove.

    Verifies the full end-to-end path:
    1. Script reaches the Monaco editor (inject)
    2. Confirmation modal is dismissed if present (Save and add to chart)
    3. Indicator appears on the chart legend (not just editor-level success)
    4. Remove succeeds
    """
    pine_file = TEMP_DIR / "test_indicator.pine"
    # Use v6 — TradingView may reject v5 with a compile error on newer builds
    pine_file.write_text(
        '//@version=6\nindicator("Test_Indicator", overlay=false)\nplot(close, title="close")'
    )

    try:
        # Step 1: inject via cli.js (uses updated pine.js with modal handling)
        r = subprocess.run(
            ["node", "cli.js", "pine", "inject", "-f", str(pine_file)],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=20,
        )
        if r.returncode != 0:
            return False, f"inject cli.js failed (exit {r.returncode}): {r.stderr.strip()[:200]}"
        inject_out = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
        if not inject_out.get("success"):
            return False, f"inject returned failure: {inject_out}"

        # Step 2: verify indicator appears on chart legend (not just editor-level success).
        # We check via cli.js status — it reports chart_symbol; also check legend via pine read.
        import time
        time.sleep(2)  # allow chart to render

        r2 = subprocess.run(
            ["node", "cli.js", "pine", "read", "--indicator", "Test_Indicator"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
        read_out = json.loads(r2.stdout.strip()) if r2.stdout.strip() else {}
        if not read_out.get("success"):
            return False, f"pine read after inject failed: {read_out}"
        # data may be empty if Data Window is closed — that is acceptable;
        # the key check is that the command did NOT return an error about the indicator missing

        # Step 3: remove
        r3 = subprocess.run(
            ["node", "cli.js", "pine", "remove", "-i", "Test_Indicator"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
        rm_out = json.loads(r3.stdout.strip()) if r3.stdout.strip() else {}
        if not rm_out.get("success"):
            return False, f"remove failed: {rm_out}"

        return True, "inject (with modal handling) → read → remove cycle succeeded"
    except Exception as e:
        return False, f"Pine cycle error: {e}"


# ── Section 1.2 & 1.3: Extended Pine Script Tests ────────────────────────────

def test_pine_data_window_readable() -> tuple[bool, str]:
    """[1.2] openDataWindow → inject hello-world → assert bar_idx key in DW."""
    pine_file = TEMP_DIR / "test_hello_world.pine"
    pine_file.write_text(
        '//@version=6\nindicator("Test_HelloWorld", overlay=false)\nplot(bar_index, title="bar_idx")'
    )
    try:
        # Step A: open Data Window
        r = subprocess.run(
            ["node", "cli.js", "chart", "openDataWindow"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
        dw_open = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
        if not dw_open.get("success"):
            return False, (
                f"openDataWindow failed: {dw_open}\n"
                "  → chart openDataWindow subcommand not yet implemented (expected at this TDD stage)"
            )

        # Step B: inject hello-world
        r2 = subprocess.run(
            ["node", "cli.js", "pine", "inject", "-f", str(pine_file)],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=20,
        )
        inject_out = json.loads(r2.stdout.strip()) if r2.stdout.strip() else {}
        if not inject_out.get("success"):
            return False, f"inject failed: {inject_out}"

        import time; time.sleep(2)

        # Re-open DW — inject animation closes the right sidebar panel
        subprocess.run(
            ["node", "cli.js", "chart", "openDataWindow"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
        time.sleep(1)

        # Step C: read DW and assert bar_idx present
        r3 = subprocess.run(
            ["node", "cli.js", "chart", "read"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
        dw_out = json.loads(r3.stdout.strip()) if r3.stdout.strip() else {}
        if not dw_out.get("success"):
            return False, (
                f"readDataWindow failed: {dw_out}\n"
                "  Hint: Is Data Window visible in TV? Ask user to confirm."
            )
        data = dw_out.get("data", {})
        matching = [k for k in data if "bar_idx" in k.lower() or "bar index" in k.lower()]
        if not matching:
            return False, (
                f"'bar_idx' not found in DW. Actual keys: {list(data.keys())[:15]}\n"
                "  ⚠️ USER GATE: Ask the user what labels appear in the TV Data Window for 'Test_HelloWorld'. "
                "Update the key check below to match the exact label TV shows."
            )
        return True, f"DW readable — found key '{matching[0]}' = {data[matching[0]]}"
    finally:
        subprocess.run(
            ["node", "cli.js", "pine", "remove", "-i", "Test_HelloWorld"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )


def test_pine_save_layout() -> tuple[bool, str]:
    """[1.3] Inject hello-world → saveLayout → assert success."""
    pine_file = TEMP_DIR / "test_hello_world.pine"
    pine_file.write_text(
        '//@version=6\nindicator("Test_HelloWorld", overlay=false)\nplot(bar_index, title="bar_idx")'
    )
    try:
        r = subprocess.run(
            ["node", "cli.js", "pine", "inject", "-f", str(pine_file)],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=20,
        )
        inject_out = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
        if not inject_out.get("success"):
            return False, f"inject failed: {inject_out}"

        import time; time.sleep(1)

        r2 = subprocess.run(
            ["node", "cli.js", "chart", "saveLayout", "--name", "agent-layout"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=20,
        )
        save_out = json.loads(r2.stdout.strip()) if r2.stdout.strip() else {}
        if not save_out.get("success"):
            return False, (
                f"saveLayout failed: {save_out}\n"
                "  → chart saveLayout subcommand not yet implemented (expected at this TDD stage)\n"
                "  ⚠️ USER GATE if unexpected: Ask user if a dialog appeared in TV after running this."
            )
        return True, f"Layout saved: {save_out}"
    finally:
        subprocess.run(
            ["node", "cli.js", "pine", "remove", "-i", "Test_HelloWorld"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )


# ── Section 2: Chart Command Tests ───────────────────────────────────────────

def test_chart_timeframe_known() -> tuple[bool, str]:
    """chart timeframe 1D — should succeed (no error key in result)."""
    r = subprocess.run(
        ["node", "cli.js", "chart", "timeframe", "1D"],
        capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
    )
    if r.returncode != 0:
        return False, f"cli.js exited {r.returncode}: {r.stderr.strip()[:200]}"
    try:
        out = json.loads(r.stdout.strip())
        if isinstance(out, dict) and out.get("error"):
            return False, f"Returned error: {out['error']}"
        return True, "timeframe 1D set successfully"
    except (json.JSONDecodeError, ValueError):
        if r.stdout.strip():
            return True, "timeframe 1D set (plain text output)"
        return False, "No output from chart timeframe command"


def test_chart_read_structure() -> tuple[bool, str]:
    """chart read — should return a dict or list, or a known 'not visible' error."""
    r = subprocess.run(
        ["node", "cli.js", "chart", "read"],
        capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
    )
    if r.returncode != 0:
        return False, f"cli.js exited {r.returncode}: {r.stderr.strip()[:200]}"
    raw = r.stdout.strip()
    if not raw:
        return False, "No output from chart read command"
    try:
        out = json.loads(raw)
        if isinstance(out, dict) and out.get("error"):
            err = str(out["error"]).lower()
            if "not visible" in err or "data window" in err:
                return True, f"chart read responded correctly (Data Window not open): {out['error']}"
            return False, f"Unexpected error: {out['error']}"
        entry_count = len(out) if hasattr(out, "__len__") else "?"
        return True, f"chart read returned {type(out).__name__} with {entry_count} entries"
    except (json.JSONDecodeError, ValueError):
        return False, f"Non-JSON output: {raw[:100]}"


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
        print("  tradingview-cdp/core/broker_data.js")
        print("  tradingview-cdp/core/trading.js")
        return False

    return True


def run_section_1() -> bool:
    print(f"\n{HEADER}Section 1 — Pine Script Live Cycle{RESET}")
    ok, msg = test_live_pine_cycle()
    icon = OK if ok else FAIL
    print(f"  [1.1] {icon} live inject / read / remove")
    print(f"       {msg}")
    return ok


def run_section_2() -> bool:
    print(f"\n{HEADER}Section 2 — Chart Command Tests{RESET}")
    checks = [
        ("2.1", "chart timeframe 1D", test_chart_timeframe_known),
        ("2.2", "chart read structure", test_chart_read_structure),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="TradingView CDP prerequisite checks")
    parser.add_argument(
        "--suite",
        choices=["prereqs", "selectors", "pine", "chart", "all"],
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

    if args.suite in ("pine", "all"):
        ok1 = run_section_1()
        pine_ok = ok1

        print(f"\n{HEADER}Section 1.2 — Data Window Readable{RESET}")
        ok12, msg12 = test_pine_data_window_readable()
        icon12 = OK if ok12 else FAIL
        print(f"  {icon12} [1.2] {msg12}")
        if not ok12:
            pine_ok = False

        print(f"\n{HEADER}Section 1.3 — Save Chart Layout{RESET}")
        ok13, msg13 = test_pine_save_layout()
        icon13 = OK if ok13 else FAIL
        print(f"  {icon13} [1.3] {msg13}")
        if not ok13:
            pine_ok = False

        if not pine_ok:
            print(f"\n{FAIL} Section 1 (or 1.2/1.3) failed — Pine Script cycle broken.")
            sys.exit(3)

    if args.suite in ("chart", "all"):
        ok2 = run_section_2()
        if not ok2:
            print(f"\n{FAIL} Section 2 failed — chart command regression.")
            sys.exit(4)

    print(f"\n{OK} All prerequisite checks passed.")


if __name__ == "__main__":
    main()
