#!/usr/bin/env python3
"""
tv_client.py - Core TradingView CLI client.

This is the single source of truth for the path to the Node.js CLI.
All other scripts import tv_call / is_tv_running / tv_call_or_fallback from here.

Path layout:
  plugins/tradingview/scripts/tv_client.py
  parents[0] = scripts/
  parents[1] = tradingview/
  parents[2] = plugins/
  parents[3] = repo root
"""

import json
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
# Owned Node.js CDP client — no dependency on temp/tradingview-mcp
TV_CLI = REPO_ROOT / "plugins" / "tradingview" / "node" / "cli.js"
TV_NODE_MODULES = REPO_ROOT / "plugins" / "tradingview" / "node" / "node_modules"
TV_PORT = 9222


def is_tv_running() -> bool:
    """
    Return True only if TradingView Desktop is on port 9222.

    A plain socket check is insufficient — Chrome DevTools also binds 9222.
    This queries the CDP /json/list endpoint and looks for a page target
    whose URL contains 'tradingview', which only matches TradingView Desktop.
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

    Args:
        *args: CLI arguments passed after `node <TV_CLI>`.
        timeout: Subprocess timeout in seconds (default 10).

    Returns:
        Parsed JSON output (dict or list).

    Raises:
        FileNotFoundError: If node or the CLI script is not found.
        RuntimeError: If the CLI exits with a non-zero return code.
        json.JSONDecodeError: If stdout is not valid JSON.
    """
    if not TV_CLI.exists():
        raise FileNotFoundError(
            f"TradingView CLI not found at {TV_CLI}. "
            "Run: cd plugins/tradingview/node && npm install"
        )

    cmd = ["node", str(TV_CLI)] + [str(a) for a in args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"TradingView CLI error (exit {result.returncode}): {result.stderr.strip()}"
        )

    return json.loads(result.stdout)


def tv_call_or_fallback(*args, fallback_fn, timeout: int = 10):
    """
    Try tv_call(*args). If TradingView is unavailable or any error occurs,
    call fallback_fn() instead.

    Returns:
        (result, source) where source is 'tradingview' or 'fallback'.
    """
    if not is_tv_running():
        return fallback_fn(), "fallback"

    try:
        result = tv_call(*args, timeout=timeout)
        return result, "tradingview"
    except Exception:
        return fallback_fn(), "fallback"
