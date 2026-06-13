#!/usr/bin/env python3
"""
tv_client.py - Core TradingView CLI client.

The Node.js CDP engine lives at PROJECT_ROOT/tradingview-cdp/.

Resolution order:
  1. TV_CDP_DIR environment variable (explicit override -- works in CI, Docker, post-install)
  2. Walk up from this file's real location looking for tradingview-cdp/cli.js
  3. Fail with clear, actionable setup instructions

This module is the SINGLE SOURCE OF TRUTH for Node.js path resolution.
All other TradingView Python scripts MUST import TV_NODE_DIR and TV_CLI from here.
"""

import json
import os
import sys
import subprocess
import urllib.request
from pathlib import Path


def _find_cdp_dir() -> Path:
    """
    Locate the tradingview-cdp Node.js package.
    """
    env_path = os.environ.get("TV_CDP_DIR")
    if env_path:
        p = Path(env_path).resolve()
        if (p / "cli.js").exists():
            return p
        raise FileNotFoundError(
            f"TV_CDP_DIR is set to '{env_path}' but 'cli.js' was not found there."
        )

    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "tradingview-cdp"
        if (candidate / "cli.js").exists():
            return candidate
        if current == current.parent:
            break
        current = current.parent

    raise FileNotFoundError(
        "\n"
        "+============================================================+\n"
        "|  TradingView CDP Engine Not Found                          |\n"
        "+============================================================+\n"
        "|                                                            |\n"
        "|  Expected at: <project-root>/tradingview-cdp/              |\n"
        "|                                                            |\n"
        "|  Setup:                                                    |\n"
        "|    cd <project-root>/tradingview-cdp                       |\n"
        "|    npm ci                                             |\n"
        "|                                                            |\n"
        "|  Or set the environment variable:                          |\n"
        "|    export TV_CDP_DIR=/path/to/tradingview-cdp              |\n"
        "|                                                            |\n"
        "|  See: plugins/tradingview/README.md for full setup guide   |\n"
        "+============================================================+\n"
    )

_CDP_MISSING_MSG = None
try:
    TV_NODE_DIR = _find_cdp_dir()
    TV_CLI = TV_NODE_DIR / "cli.js"
    TV_NODE_MODULES = TV_NODE_DIR / "node_modules"
    REPO_ROOT = TV_NODE_DIR.parent
except FileNotFoundError as e:
    TV_NODE_DIR = Path(".")
    TV_CLI = Path("./cli.js")
    TV_NODE_MODULES = Path("./node_modules")
    REPO_ROOT = Path(".")
    _CDP_MISSING_MSG = str(e)

TV_PORT = int(os.environ.get("TV_CDP_PORT", "9222"))


def validate_cdp_installation() -> dict:
    """
    Validate that the CDP engine is properly installed and ready.
    Returns a status dict. Call this from health checks.
    """
    issues = []

    if _CDP_MISSING_MSG:
        issues.append(_CDP_MISSING_MSG)
        return {
            "cdp_engine_path": "Not Found",
            "cli_path": "Not Found",
            "installed": False,
            "issues": issues
        }

    if not TV_CLI.exists():
        issues.append(f"cli.js not found at {TV_CLI}")

    if not TV_NODE_MODULES.exists():
        issues.append(
            f"node_modules/ not found at {TV_NODE_MODULES}. "
            f"Run: cd {TV_NODE_DIR} && npm ci"
        )
    elif not (TV_NODE_MODULES / "chrome-remote-interface").exists():
        issues.append(
            f"chrome-remote-interface not installed. "
            f"Run: cd {TV_NODE_DIR} && npm ci"
        )

    return {
        "cdp_engine_path": str(TV_NODE_DIR),
        "cli_path": str(TV_CLI),
        "installed": len(issues) == 0,
        "issues": issues
    }

def is_tv_running() -> bool:
    """
    Return True only if TradingView Desktop is on port 9222.
    """
    try:
        req = urllib.request.urlopen(
            f"http://localhost:{TV_PORT}/json/list", timeout=1
        )
        targets = json.loads(req.read())
        return any(
            t.get("type") == "page" and "tradingview" in t.get("url", "").lower()
            for t in targets
        )
    except Exception:
        return False


def tv_call(*args, timeout: int = 10):
    """
    Call the TradingView CLI with the given arguments and return parsed JSON.
    """
    if _CDP_MISSING_MSG:
        raise FileNotFoundError(_CDP_MISSING_MSG)

    if not TV_CLI or not TV_CLI.exists():
        raise FileNotFoundError(
            f"TradingView CLI not found at {TV_CLI}. "
            f"Run: cd {TV_NODE_DIR} && npm ci"
        )

    cmd = ["node", str(TV_CLI)] + [str(a) for a in args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(TV_NODE_DIR)
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"TradingView CLI error (exit {result.returncode}): {result.stderr.strip()}"
        )

    return json.loads(result.stdout)


def run_node_module_raw(js_code: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Execute inline ES module code with the CDP engine's node_modules in scope.
    """
    if _CDP_MISSING_MSG:
        raise FileNotFoundError(_CDP_MISSING_MSG)

    return subprocess.run(
        ["node", "--input-type=module"],
        input=js_code,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(TV_NODE_DIR)
    )

def run_node_module(js_code: str, timeout: int = 30) -> dict:
    """
    Execute inline ES module code and parse the returned JSON.
    """
    result = run_node_module_raw(js_code, timeout=timeout)
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(f"Node.js error (exit {result.returncode}): {result.stderr.strip()[:500]}")
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip(), "stderr": result.stderr.strip()}

def tv_call_or_fallback(*args, fallback_fn, timeout: int = 10):
    """
    Try tv_call(*args). If TradingView is unavailable or any error occurs,
    call fallback_fn() instead.
    """
    if not is_tv_running():
        return fallback_fn(), "fallback"

    try:
        result = tv_call(*args, timeout=timeout)
        return result, "tradingview"
    except Exception:
        return fallback_fn(), "fallback"
