#!/usr/bin/env python3
"""
run_tests.py — T0 Compile/Syntax Gate + T0.5 Bridge Smoke

T0: TypeScript compile + Python syntax + Node syntax checks.
    All failures are CRITICAL — no other tier runs if any T0 check fails.

T0.5: portfolio_action.py subprocess smoke — verifies the bridge is intact.
      If this returns empty or non-zero, abort before all other tiers.

Usage:
    python3 tests/run_tests.py           # run T0 + T0.5
    python3 tests/run_tests.py --t0-only # run T0 only
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "investment_screener/backend/tests/fixtures"

CRITICAL = "\033[91m[CRITICAL]\033[0m"
OK = "\033[92m[OK]\033[0m"
HEADER = "\033[1m"
RESET = "\033[0m"


def run(cmd: list[str], cwd: Path | None = None, label: str = "") -> bool:
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


def t0_typescript() -> bool:
    print(f"\n{HEADER}T0 — TypeScript compile{RESET}")
    screener = REPO_ROOT / "investment_screener"
    ok = True
    ok &= run(["npm", "run", "build", "-w", "backend"],  cwd=screener, label="backend build")
    ok &= run(["npm", "run", "build", "-w", "frontend"], cwd=screener, label="frontend build")
    return ok


def t0_python_syntax() -> bool:
    print(f"\n{HEADER}T0 — Python syntax checks{RESET}")
    scripts = [
        REPO_ROOT / "investment_screener/backend/py_services/place_order.py",
        REPO_ROOT / "investment_screener/backend/py_services/portfolio_action.py",
        REPO_ROOT / "plugins/tradingview/scripts/tv_cancel_order.py",
        REPO_ROOT / "plugins/tradingview/scripts/tv_modify_order.py",
        REPO_ROOT / "plugins/tradingview/scripts/tv_get_orders.py",
    ]
    ok = True
    for script in scripts:
        ok &= run(
            ["python3", "-m", "py_compile", str(script)],
            label=script.name,
        )
    return ok


def t0_node_syntax() -> bool:
    print(f"\n{HEADER}T0 — Node.js syntax checks{RESET}")
    files = [
        REPO_ROOT / "plugins/tradingview/node/core/trading.js",
        REPO_ROOT / "plugins/tradingview/node/core/broker_data.js",
    ]
    ok = True
    for f in files:
        ok &= run(["node", "--check", str(f)], label=f.name)
    return ok


def t0_5_bridge_smoke() -> bool:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="T0 + T0.5 test gates")
    parser.add_argument("--t0-only", action="store_true", help="Skip T0.5")
    args = parser.parse_args()

    print(f"\n{HEADER}=== InvestmentToolkit Test Runner ==={RESET}")
    failed: list[str] = []

    for tier, fn in [
        ("T0 TypeScript",     t0_typescript),
        ("T0 Python syntax",  t0_python_syntax),
        ("T0 Node syntax",    t0_node_syntax),
    ]:
        if not fn():
            failed.append(tier)
            print(f"\n{CRITICAL} {tier} FAILED — aborting remaining tiers.")
            sys.exit(1)

    if not args.t0_only:
        if not t0_5_bridge_smoke():
            failed.append("T0.5")
            print(f"\n{CRITICAL} T0.5 FAILED — aborting remaining tiers.")
            sys.exit(1)

    print(f"\n{OK} All gates passed.")


if __name__ == "__main__":
    main()
