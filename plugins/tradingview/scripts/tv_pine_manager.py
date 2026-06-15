"""
tv_pine_manager.py — Python wrapper around the Node CLI pine commands.

Delegates to `node cli.js pine <subcommand>` in the tradingview-cdp directory.
Output is always JSON parsed from stdout.

Usage (CLI):
    python3 tv_pine_manager.py inject --file /path/to/script.pine
    python3 tv_pine_manager.py read --indicator AI_Custom_TA
    python3 tv_pine_manager.py remove --indicator AI_Custom_TA

Args (module):
    inject_pine(file_path: str) -> dict
    read_pine(indicator_name: str) -> dict
    remove_pine(indicator_name: str) -> dict
"""

import argparse
import json
import sys
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
from tv_client import tv_call

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent
TEMP_DIR = _REPO_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)


def _run_node_cli(*args: str) -> dict:
    """Run `node cli.js pine <args>` and return parsed JSON output.

    Args:
        *args: Subcommand and flags forwarded to the pine router.

    Returns:
        Parsed JSON dict from stdout.
    """
    try:
        return tv_call("pine", *args)
    except Exception as e:
        return {"success": False, "error": str(e)}


def inject_pine(file_path: str) -> dict:
    """Inject a Pine Script file into the active TradingView chart.

    Args:
        file_path: Absolute path to the .pine script file.

    Returns:
        dict with 'success' bool and optional 'error' string.
    """
    return _run_node_cli("inject", "--file", file_path)


def read_pine(indicator_name: str) -> dict:
    """Read current indicator values from the TradingView Data Window.

    Args:
        indicator_name: Display name of the indicator on the chart.

    Returns:
        dict with 'success' bool and 'data' dict of indicator values.
    """
    return _run_node_cli("read", "--indicator", indicator_name)


def remove_pine(indicator_name: str) -> dict:
    """Remove a named indicator from the active TradingView chart.

    Args:
        indicator_name: Display name of the indicator to remove.

    Returns:
        dict with 'success' bool and optional 'error' string.
    """
    return _run_node_cli("remove", "--indicator", indicator_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TradingView Pine Script manager")
    parser.add_argument("action", choices=["inject", "read", "remove"])
    parser.add_argument("--file", help="Path to .pine script file (inject only)")
    parser.add_argument("--indicator", help="Indicator display name (read/remove)")
    parsed = parser.parse_args()

    if parsed.action == "inject":
        if not parsed.file:
            parser.error("--file is required for inject")
        print(json.dumps(inject_pine(parsed.file)))
    elif parsed.action == "read":
        if not parsed.indicator:
            parser.error("--indicator is required for read")
        print(json.dumps(read_pine(parsed.indicator)))
    elif parsed.action == "remove":
        if not parsed.indicator:
            parser.error("--indicator is required for remove")
        print(json.dumps(remove_pine(parsed.indicator)))
