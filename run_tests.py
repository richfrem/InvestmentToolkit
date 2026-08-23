#!/usr/bin/env python3
"""
run_tests.py — T0 Compile/Syntax Gate + T0.5 Bridge Smoke
=========================================================

Purpose:
    T0: TypeScript compile + Python syntax + Node syntax checks.
    All failures are CRITICAL — no other tier runs if any T0 check fails.

    T0.5: portfolio_action.py subprocess smoke — verifies the bridge is intact.
    If this returns empty or non-zero, abort before all other tiers.

Layer:
    Codify

Key Input Dependencies:
    - investment_screener/package.json (TypeScript project config)
    - symlinks.json (Symlink verification rules)
    - plugins/ (Active Python plugins directory)

Usage:
    python3 run_tests.py           # run T0 + T0.5
    python3 run_tests.py --unit    # run T0 + T0.5 + T1 unit tests (pytest)
    python3 run_tests.py --t0-only # run T0 only
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, List

REPO_ROOT = Path(__file__).resolve().parent
FIXTURES = REPO_ROOT / "investment_screener/backend/tests/fixtures"

CRITICAL = "\033[91m[CRITICAL]\033[0m"
OK = "\033[92m[OK]\033[0m"
HEADER = "\033[1m"
RESET = "\033[0m"


# External comment: Helper to run a command and report status
def run(cmd: List[str], cwd: Path = None, label: str = "") -> bool:
    """Run a command, print result, return True on success."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or REPO_ROOT))
    if result.returncode == 0:
        print(f"  {OK} {label}")
        return True
    print(f"  {CRITICAL} {label}")
    if result.stderr:
        for line in result.stderr.strip().splitlines()[:15]:
            print(f"    {line}")
    if result.stdout:
        for line in result.stdout.strip().splitlines()[:10]:
            print(f"    {line}")
    return False


# External comment: Compile TypeScript packages
def t0_typescript() -> bool:
    """Builds backend and frontend workspaces using npm."""
    print(f"\n{HEADER}T0 — TypeScript compile{RESET}")
    screener = REPO_ROOT / "investment_screener"
    ok = True
    ok &= run(["npm", "run", "build", "-w", "backend"],  cwd=screener, label="backend build")
    ok &= run(["npm", "run", "build", "-w", "frontend"], cwd=screener, label="frontend build")
    return ok


# External comment: Verify all active python scripts parse without errors
def t0_python_syntax() -> bool:
    """Runs compile syntax verification over all Python scripts."""
    print(f"\n{HEADER}T0 — Python syntax checks{RESET}")
    scripts = [
        REPO_ROOT / "investment_screener/backend/py_services/portfolio_action.py",
    ]
    for s in glob.glob(str(REPO_ROOT / "plugins/tradingview/scripts/*.py")):
        scripts.append(Path(s))
        
    ok = True
    for script in scripts:
        ok &= run(
            ["python3", "-m", "py_compile", str(script)],
            label=script.name,
        )
    return ok


# External comment: Scans repository to ensure forbidden folders are not referenced in text files
def t0_path_regression() -> bool:
    """Audits the repo for legacy paths (e.g. tradingview-mcp)."""
    print(f"\n{HEADER}T0 — Stale Path Regression{RESET}")
    forbidden = [
        "plugins/tradingview/node",
        "temp/tradingview-mcp",
    ]
    allowed = {
        "ADRs/024-tradingview-cdp-shared-runtime-dependency.md",
        "ADRs/023-tradingview-test-harness.md",
        "adrs/024-tradingview-cdp-shared-runtime-dependency.md",
        "adrs/023-tradingview-test-harness.md",
        "temp/bundles/tradingview-symlink-review/post-implementation/payload.md",
        "temp/bundles/tradingview-symlink-review/payload.md",
        "run_tests.py",
    }
    
    ok = True
    for root, _, files in os.walk(str(REPO_ROOT)):
        if any(p in root for p in [".git", "node_modules", "venv", "temp", ".agents", "docs/superpowers", "tasks/done", ".claude", ".worktrees"]):
            continue
        for f in files:
            if f.endswith(".png") or f.endswith(".svg"):
                continue
            path = Path(root) / f
            rel_path = str(path.relative_to(REPO_ROOT))
            if rel_path in allowed:
                continue
            try:
                text = path.read_text(errors="ignore")
                for s in forbidden:
                    if s in text:
                        print(f"  {CRITICAL} {rel_path} still references stale path: {s}")
                        ok = False
            except Exception:
                pass
    if ok:
        print(f"  {OK} No stale runtime paths found")
    return ok


# External comment: Health check verification helper
def verify_script_health(cwd: Path, label: str) -> bool:
    """Executes the health check script and validates JSON result."""
    result = subprocess.run(
        ["python3", str(REPO_ROOT / "plugins/tradingview/scripts/tv_health_check.py"), "--json"],
        capture_output=True, text=True, cwd=str(cwd)
    )
    try:
        data = json.loads(result.stdout.strip())
        if data.get("npm") is True:
            print(f"  {OK} {label}")
            return True
        else:
            print(f"  {CRITICAL} {label} - npm not resolved to true")
            return False
    except Exception:
        print(f"  {CRITICAL} {label} - output not valid JSON: {result.stdout[:100]} Error: {result.stderr[:100]}")
        return False


# External comment: Verify scripts behavior across different working directories
def t0_symlink_cwd_invariance() -> bool:
    """Validates CWD invariance and path variables override logic."""
    print(f"\n{HEADER}T0 — CWD / Symlink Invariance{RESET}")
    ok = True
    
    # Run from arbitrary cwd
    ok &= verify_script_health(Path("/"), "tv_health_check.py from root (/)")
    
    # Run from repo root
    ok &= verify_script_health(REPO_ROOT, "tv_health_check.py from repo root")
    
    # Run from symlink path
    skill_dir = REPO_ROOT / "plugins/tradingview/skills/get-orders"
    if skill_dir.exists():
        ok &= verify_script_health(skill_dir, "tv_health_check.py from skill dir")
    
    # TV_CDP_DIR override test
    env = os.environ.copy()
    env["TV_CDP_DIR"] = "/tmp/fake-tradingview-cdp"
    result = subprocess.run(
        ["python3", str(REPO_ROOT / "plugins/tradingview/scripts/tv_health_check.py"), "--json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), env=env
    )
    combined = result.stdout + result.stderr
    if result.returncode != 0 and "not found" in combined:
        print(f"  {OK} TV_CDP_DIR override test passed (failed correctly with bad path)")
    else:
        print(f"  {CRITICAL} TV_CDP_DIR override test failed. Exit={result.returncode} stdout={result.stdout[:200]}")
        ok = False
        
    return ok


# External comment: Verify Node.js javascript files parse correctly
def t0_node_syntax() -> bool:
    """Checks compilation syntax of JavaScript client dependencies."""
    print(f"\n{HEADER}T0 — Node.js syntax checks{RESET}")
    files = [
        REPO_ROOT / "tradingview-cdp/core/trading.js",
        REPO_ROOT / "tradingview-cdp/core/broker_data.js",
    ]
    ok = True
    for f in files:
        ok &= run(["node", "--check", str(f)], label=f.name)
    return ok


# External comment: Validate self-evolution Map Debt markdown registry
def t0_map_debt() -> bool:
    """Audits map-debt.md using evolution audit script."""
    print(f"\n{HEADER}T0 — Map Debt registry audit{RESET}")
    script = REPO_ROOT / ".agents/skills/self-evolution/scripts/audit_map_debt.py"
    return run(["python3", str(script)], label="map-debt.md audit")


# External comment: Smoke test the python bridge execution via symlink
def t0_5_bridge_smoke() -> bool:
    """Validates the portfolio action bridge script runs and outputs valid JSON."""
    print(f"\n{HEADER}T0.5 — Bridge smoke (portfolio_action.py via symlink){RESET}")
    symlink = REPO_ROOT / "investment_screener/backend/py_services/portfolio_action.py"
    r = subprocess.run(
        [
            "python3", str(symlink),
            "--all",
            "--portfolio", str(FIXTURES / "portfolio.test.json"),
            "--target",   str(FIXTURES / "target_portfolio.test.json"),
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        print(f"  {CRITICAL} portfolio_action.py via symlink — non-zero exit")
        print(f"    stderr: {r.stderr.strip()}")
        return False
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"  {CRITICAL} portfolio_action.py via symlink — invalid JSON output")
        print(f"    stdout: {r.stdout[:200]}")
        return False
    if not data:
        print(f"  {CRITICAL} portfolio_action.py via symlink — empty action map")
        return False
    print(f"  {OK} portfolio_action.py via symlink — {len(data)} tickers: {list(data)}")
    return True


# External comment: Optional T1 Python unit test runner
def t1_unit_tests() -> bool:
    """Runs pytest across plugin and backend unit test suites."""
    print(f"\n{HEADER}T1 — Python Unit Tests (pytest){RESET}")
    cmd = [
        "python3", "-m", "pytest",
        "plugins/tradingview/tests/test_tv_thesis_overlay.py",
        "plugins/tradingview/tests/test_tv_alert_reconcile.py",
        "plugins/tradingview/tests/test_tv_create_alerts.py",
        "plugins/tradingview/tests/test_ta_sweep_batch.py",
        "-q",
    ]
    return run(cmd, label="TradingView Plugin Unit Tests")


# External comment: Main entry point orchestrator for execution
def main() -> None:
    """
    Orchestration gate runner that runs T0 and T0.5 verification routines.
    """
    parser = argparse.ArgumentParser(description="T0 + T0.5 + T1 test gates")
    parser.add_argument("--t0-only", action="store_true", help="Skip T0.5 and T1")
    parser.add_argument("--unit", "-u", action="store_true", help="Run T1 Python unit tests (pytest)")
    args = parser.parse_args()

    print(f"\n{HEADER}=== InvestmentToolkit Test Runner ==={RESET}")

    for _, fn in [
        ("T0 TypeScript",     t0_typescript),
        ("T0 Python syntax",  t0_python_syntax),
        ("T0 Node syntax",    t0_node_syntax),
        ("T0 Path regression", t0_path_regression),
        ("T0 Invariance",      t0_symlink_cwd_invariance),
        ("T0 Map Debt",        t0_map_debt),
    ]:
        if not fn():
            print(f"\n{CRITICAL} Gate FAILED — aborting remaining tiers.")
            sys.exit(1)

    if not args.t0_only:
        if not t0_5_bridge_smoke():
            print(f"\n{CRITICAL} T0.5 FAILED — aborting remaining tiers.")
            sys.exit(1)

    if args.unit:
        if not t1_unit_tests():
            print(f"\n{CRITICAL} T1 Unit Tests FAILED.")
            sys.exit(1)

    print(f"\n{OK} All gates passed.")


if __name__ == "__main__":
    main()
