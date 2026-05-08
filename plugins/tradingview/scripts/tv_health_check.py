#!/usr/bin/env python3
"""
tv_health_check.py - Verify TradingView Desktop is reachable and the CLI is set up.

Usage:
    python3 tv_health_check.py          # human-readable table
    python3 tv_health_check.py --json   # machine-readable JSON

Checks:
    1. Is port 9222 reachable? (socket test)
    2. Does `node ... status` return success?
    3. Is npm installed in temp/tradingview-mcp/ (node_modules exists)?

Exit code 0 if all checks pass, 1 otherwise.
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tv_client import REPO_ROOT, TV_CLI, TV_NODE_MODULES, TV_PORT, is_tv_running, tv_call


def run_checks() -> dict:
    """Run all health checks and return a results dict."""
    # Check 1 — CDP port reachable
    port_ok = is_tv_running()

    # Check 2 — CLI `status` command responds
    cli_ok = False
    cli_message = ""
    if port_ok:
        try:
            result = tv_call("status", timeout=5)
            cli_ok = result.get("success", False) or result.get("connected", False)
            cli_message = result.get("message", str(result))
        except Exception as e:
            cli_message = str(e)
    else:
        cli_message = "Skipped — port not reachable"

    # Check 3 — node_modules exists
    npm_ok = TV_NODE_MODULES.exists()
    npm_message = (
        "node_modules found"
        if npm_ok
        else f"Missing! Run: cd {REPO_ROOT / 'plugins' / 'tradingview' / 'node'} && npm install"
    )

    all_ok = port_ok and cli_ok and npm_ok

    return {
        "status": "ok" if all_ok else "error",
        "port": port_ok,
        "cli": cli_ok,
        "npm": npm_ok,
        "message": (
            "All checks passed — TradingView is connected and CLI is ready."
            if all_ok
            else (
                "TradingView Desktop not detected. "
                "Launch with: python3 plugins/tradingview/scripts/tv_launch.py"
                if not port_ok
                else f"CLI check failed: {cli_message}"
            )
        ),
        "details": {
            "port_9222": "reachable" if port_ok else "not reachable",
            "cli_status": cli_message if cli_message else ("ok" if cli_ok else "no response"),
            "npm_modules": npm_message,
            "cli_path": str(TV_CLI),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check TradingView Desktop health and CLI readiness."
    )
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output JSON instead of human-readable table")
    args = parser.parse_args()

    checks = run_checks()

    if args.json_out:
        print(json.dumps(checks, indent=2))
    else:
        # Human-readable output
        status_icon = "OK" if checks["status"] == "ok" else "ERROR"
        print(f"\nTradingView Health Check [{status_icon}]")
        print("=" * 45)

        def icon(ok: bool) -> str:
            return "[PASS]" if ok else "[FAIL]"

        print(f"  {icon(checks['port'])}  Port {TV_PORT} reachable   — {checks['details']['port_9222']}")
        print(f"  {icon(checks['cli'])}  CLI status command  — {checks['details']['cli_status']}")
        print(f"  {icon(checks['npm'])}  npm node_modules    — {checks['details']['npm_modules']}")
        print()
        print(f"  {checks['message']}")
        print()

        if not checks["npm"]:
            print(
                f"  Fix: cd {REPO_ROOT / 'plugins' / 'tradingview' / 'node'} && npm install\n"
            )
        if not checks["port"]:
            print(
                "  Launch TradingView:\n"
                "    python3 plugins/tradingview/scripts/tv_launch.py\n"
                "  Or manually:\n"
                "    open -a TradingView --args --remote-debugging-port=9222\n"
            )

    sys.exit(0 if checks["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
