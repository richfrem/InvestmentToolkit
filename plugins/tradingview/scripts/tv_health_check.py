#!/usr/bin/env python3
"""
tv_health_check.py (Python Utility)
====================================

Purpose:
    Comprehensive diagnostic health check for TradingView Desktop and the CDP automation engine.
    Verifies port 9222 connectivity, Node.js CLI responsiveness, npm dependencies,
    default Pine Script indicator library presence, and domain model SQLite readiness.

Layer: Plugins / TradingView / Scripts

Usage Examples:
    # Human-readable diagnostic output table:
    python3 plugins/tradingview/scripts/tv_health_check.py

    # Machine-readable JSON output:
    python3 plugins/tradingview/scripts/tv_health_check.py --json

Key Functions:
    - run_checks() — Executes all diagnostic checks and aggregates readiness status
    - main()       — CLI entry point with colored table / JSON output formatters

Key Input Dependencies:
    - tradingview-cdp/ (Node.js CDP Engine & node_modules)
    - plugins/tradingview/assets/pinescript-indicators/ (Pine library)
    - investment_screener/backend/data/domain_model.sqlite (Domain Database)
"""

import sys
import json
import argparse
import os
from pathlib import Path

def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")

sys.path.insert(0, str(_find_scripts_dir()))
from tv_client import TV_CLI, TV_NODE_MODULES, TV_PORT, TV_NODE_DIR, is_tv_running, tv_call, validate_cdp_installation

REPO_ROOT = TV_NODE_DIR.parent
PINE_DIR = REPO_ROOT / "plugins" / "tradingview" / "assets" / "pinescript-indicators"
DB_FILE = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"


def run_checks() -> dict:
    """
    Run all health checks and return a results dict.

    Returns:
        Dict with keys: status, port, cli, npm, pine, db, message, details.
    """
    # Check 1 — CDP port reachable
    port_ok = is_tv_running()

    # Check 2 — CLI `status` command responds
    cli_ok = False
    cli_message = ""
    if port_ok:
        try:
            result = tv_call("status", timeout=5)
            cli_ok = result.get("success", False) or result.get("cdp_connected", False)
            cli_message = result.get("message", str(result))
        except Exception as e:
            cli_message = str(e)
    else:
        cli_message = "Skipped — port not reachable"

    # Check 3 — node_modules exists
    cdp_status = validate_cdp_installation()
    npm_ok = cdp_status["installed"]
    npm_message = (
        "node_modules found"
        if npm_ok
        else "; ".join(cdp_status["issues"])
    )

    # Check 4 — Pine library presence
    default_pine = PINE_DIR / "ai-ta-levels.pine"
    pine_ok = default_pine.exists()
    pine_message = "ai-ta-levels.pine found" if pine_ok else "missing default indicator library"

    # Check 5 — Database ready
    db_ok = DB_FILE.exists()
    db_message = "domain_model.sqlite ready" if db_ok else "database file missing"

    all_ok = port_ok and cli_ok and npm_ok and pine_ok and db_ok

    return {
        "status": "ok" if all_ok else "error",
        "port": port_ok,
        "cli": cli_ok,
        "npm": npm_ok,
        "pine": pine_ok,
        "db": db_ok,
        "message": (
            "All checks passed — TradingView Desktop is connected and workspace is fully configured."
            if all_ok
            else (
                "TradingView Desktop not detected on port 9222."
                if not port_ok
                else f"Readiness issue: {cli_message if not cli_ok else (npm_message if not npm_ok else (pine_message if not pine_ok else db_message))}"
            )
        ),
        "details": {
            "port_9222": "reachable" if port_ok else "not reachable",
            "cli_status": cli_message if cli_message else ("ok" if cli_ok else "no response"),
            "npm_modules": npm_message,
            "pine_library": pine_message,
            "domain_db": db_message,
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

    try:
        checks = run_checks()
    except Exception as e:
        print(f"\nTradingView Health Check [ERROR]\n=============================================\n  Exception: {e}")
        sys.exit(1)

    if args.json_out:
        print(json.dumps(checks, indent=2))
    else:
        status_icon = "OK" if checks["status"] == "ok" else "ERROR"
        print(f"\nTradingView Health Check [{status_icon}]")
        print("=" * 45)

        def icon(ok: bool) -> str:
            return "[PASS]" if ok else "[FAIL]"

        print(f"  {icon(checks['port'])}  Port {TV_PORT} reachable   — {checks['details']['port_9222']}")
        print(f"  {icon(checks['cli'])}  CLI status command  — {checks['details']['cli_status']}")
        print(f"  {icon(checks['npm'])}  npm node_modules    — {checks['details']['npm_modules']}")
        print(f"  {icon(checks['pine'])}  Pine indicator suite— {checks['details']['pine_library']}")
        print(f"  {icon(checks['db'])}  Domain DB readiness — {checks['details']['domain_db']}")
        print()
        print(f"  {checks['message']}")
        print()

        if not checks["npm"]:
            print(
                f"  Fix: cd {TV_NODE_DIR} && npm ci\n"
            )
        if not checks["port"]:
            print(
                "  Launch TradingView Desktop with debugging enabled:\n"
                "    python3 plugins/tradingview/scripts/tv_launch.py\n"
                "  Or manually:\n"
                "    open -a TradingView --args --remote-debugging-port=9222\n"
            )

    sys.exit(0 if checks["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
