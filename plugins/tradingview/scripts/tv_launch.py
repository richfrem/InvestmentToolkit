#!/usr/bin/env python3
"""
tv_launch.py - Launch TradingView Desktop with CDP remote debugging enabled.

Usage:
    python3 tv_launch.py

On macOS: uses `open -a TradingView --args --remote-debugging-port=9222`.
Also tries the community launch script at temp/tradingview-mcp/scripts/launch_tv_debug_mac.sh.

Prints instructions if launch fails.
"""

import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tv_client import REPO_ROOT, TV_PORT, is_tv_running

LAUNCH_SCRIPT = REPO_ROOT / "temp" / "tradingview-mcp" / "scripts" / "launch_tv_debug_mac.sh"


TV_APP = Path("/Applications/TradingView.app")


def try_open_command() -> bool:
    """Try launching TradingView via macOS `open` command."""
    try:
        # Prefer direct app path for reliability; fall back to -a name lookup
        if TV_APP.exists():
            cmd = ["open", str(TV_APP), "--args", f"--remote-debugging-port={TV_PORT}"]
        else:
            cmd = ["open", "-a", "TradingView", "--args", f"--remote-debugging-port={TV_PORT}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def try_launch_script() -> bool:
    """Try the community launch script if it exists."""
    if not LAUNCH_SCRIPT.exists():
        return False
    try:
        result = subprocess.run(
            ["bash", str(LAUNCH_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main():
    if is_tv_running():
        print(f"TradingView Desktop is already running with CDP on port {TV_PORT}.")
        sys.exit(0)

    print(f"Launching TradingView Desktop with --remote-debugging-port={TV_PORT}...")

    launched = try_open_command()
    if not launched:
        print("  `open -a TradingView` failed — trying launch script...")
        launched = try_launch_script()

    if not launched:
        print(
            "\nCould not launch TradingView automatically.\n"
            "\nManual launch options:\n"
            f"  macOS:   open -a TradingView --args --remote-debugging-port={TV_PORT}\n"
            f"  Script:  bash {LAUNCH_SCRIPT}\n"
            "\nIf TradingView is not installed, download it from https://www.tradingview.com/desktop/\n"
        )
        sys.exit(1)

    # Wait up to 15 seconds for the port to become available
    print("Waiting for TradingView to start...", end="", flush=True)
    for _ in range(15):
        time.sleep(1)
        print(".", end="", flush=True)
        if is_tv_running():
            print(f"\nTradingView is ready on port {TV_PORT}.")
            sys.exit(0)

    print(
        f"\nTradingView launched but port {TV_PORT} is not yet reachable.\n"
        "Wait a few seconds and run: python3 plugins/tradingview/scripts/tv_health_check.py\n"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
