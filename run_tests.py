#!/usr/bin/env python3
"""
run_tests.py — T0 Compile/Syntax Gate + T0.5 Bridge Smoke

T0: TypeScript compile + Python syntax + Node syntax checks.
    All failures are CRITICAL — no other tier runs if any T0 check fails.

T0.5: portfolio_action.py subprocess smoke — verifies the bridge is intact.
      If this returns empty or non-zero, abort before all other tiers.

Usage:
    python3 run_tests.py           # run T0 + T0.5
    python3 run_tests.py --t0-only # run T0 only
"""

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
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
    import glob
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

def t0_path_regression() -> bool:
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
        "run_tests.py", # This file itself
    }
    
    ok = True
    import os
    for root, dirs, files in os.walk(str(REPO_ROOT)):
        if ".git" in root or "node_modules" in root or "venv" in root or "temp" in root or ".agents" in root or "docs/superpowers" in root or "tasks/done" in root or ".claude" in root or ".worktrees" in root:
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

def t0_symlink_cwd_invariance() -> bool:
    print(f"\n{HEADER}T0 — CWD / Symlink Invariance{RESET}")
    ok = True
    
    def check_health(cwd, label):
        result = subprocess.run(["python3", str(REPO_ROOT / "plugins/tradingview/scripts/tv_health_check.py"), "--json"], capture_output=True, text=True, cwd=str(cwd))
        try:
            data = json.loads(result.stdout.strip())
            if data.get("npm") is True:
                print(f"  {OK} {label}")
                return True
            else:
                print(f"  {CRITICAL} {label} - npm not resolved to true")
                return False
        except Exception as e:
            print(f"  {CRITICAL} {label} - output not valid JSON: {result.stdout[:100]} Error: {result.stderr[:100]}")
            return False

    # Run from arbitrary cwd
    ok &= check_health(Path("/"), "tv_health_check.py from root (/)")
    
    # Run from repo root
    ok &= check_health(REPO_ROOT, "tv_health_check.py from repo root")
    
    # Run from symlink path
    skill_dir = REPO_ROOT / "plugins/tradingview/skills/get-orders"
    if skill_dir.exists():
        ok &= check_health(skill_dir, "tv_health_check.py from skill dir")
    
    # TV_CDP_DIR override test
    env = os.environ.copy()
    env["TV_CDP_DIR"] = "/tmp/fake-tradingview-cdp"
    result = subprocess.run(["python3", str(REPO_ROOT / "plugins/tradingview/scripts/tv_health_check.py"), "--json"], capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)
    combined = result.stdout + result.stderr
    if result.returncode != 0 and "not found" in combined:
        print(f"  {OK} TV_CDP_DIR override test passed (failed correctly with bad path)")
    else:
        print(f"  {CRITICAL} TV_CDP_DIR override test failed. Exit={result.returncode} stdout={result.stdout[:200]}")
        ok = False
        
    return ok



def t0_node_syntax() -> bool:
    print(f"\n{HEADER}T0 — Node.js syntax checks{RESET}")
    files = [
        REPO_ROOT / "tradingview-cdp/core/trading.js",
        REPO_ROOT / "tradingview-cdp/core/broker_data.js",
    ]
    ok = True
    for f in files:
        ok &= run(["node", "--check", str(f)], label=f.name)
    return ok


def t0_map_debt() -> bool:
    print(f"\n{HEADER}T0 — Map Debt registry audit{RESET}")
    script = REPO_ROOT / ".agents/skills/self-evolution/scripts/audit_map_debt.py"
    return run(["python3", str(script)], label="map-debt.md audit")


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
        ("T0 Path regression", t0_path_regression),
        ("T0 Invariance",      t0_symlink_cwd_invariance),
        ("T0 Map Debt",        t0_map_debt),
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
