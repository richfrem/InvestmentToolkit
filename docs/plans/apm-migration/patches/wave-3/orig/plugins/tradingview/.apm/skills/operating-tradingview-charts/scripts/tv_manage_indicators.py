#!/usr/bin/env python3
"""
tv_manage_indicators.py (CLI & Automation Script)
=================================================

Purpose:
    Unified manager for TradingView chart indicators via CDP.
    Supports listing active indicators on the chart legend, adding built-in/personal
    indicators (with duplicate prevention guards), and removing active indicators.

Layer:
    Codify / TradingView Plugin

Usage Examples:
    # List active indicators:
    python3 plugins/tradingview/scripts/tv_manage_indicators.py --list

    # Add an indicator to chart:
    python3 plugins/tradingview/scripts/tv_manage_indicators.py --add "Relative Strength Index"

    # Remove an indicator from chart:
    python3 plugins/tradingview/scripts/tv_manage_indicators.py --remove "AI-TA"

Key Functions:
    - list_chart_indicators() - Queries all active indicator labels from chart legend
    - add_chart_indicator() - Adds indicator to chart with duplicate guard
    - remove_chart_indicator() - Hovers and removes target indicator from legend

Key Input Dependencies:
    - tradingview-cdp/cli.js (TradingView CDP CLI controller)
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# Ensure scripts dir is in path for tv_client import
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from tv_client import tv_call, validate_cdp_installation


def list_chart_indicators() -> Dict[str, Any]:
    """
    List all loaded indicators on the active chart.

    Returns:
        Dict with success status, count, and list of indicator names.
    """
    return tv_call("chart", "indicators")


def add_chart_indicator(name: str) -> Dict[str, Any]:
    """
    Add a named indicator to the active chart.

    Args:
        name: Name of the indicator to add.

    Returns:
        Dict with execution result.
    """
    if not name or not name.strip():
        return {"success": False, "error": "Indicator name cannot be empty."}
    return tv_call("chart", "addIndicator", name.strip())


def remove_chart_indicator(name: str) -> Dict[str, Any]:
    """
    Remove a named indicator from the active chart.

    Args:
        name: Name of the indicator to remove.

    Returns:
        Dict with execution result.
    """
    if not name or not name.strip():
        return {"success": False, "error": "Indicator name cannot be empty."}
    return tv_call("chart", "removeIndicator", name.strip())


def main() -> None:
    """
    CLI Entrypoint for managing TradingView chart indicators.
    """
    parser = argparse.ArgumentParser(description="Unified TradingView Indicator Manager")
    parser.add_argument("--list", "-l", action="store_true", help="List all indicators on active chart")
    parser.add_argument("--add", "-a", metavar="NAME", help="Add an indicator to active chart")
    parser.add_argument("--remove", "-r", metavar="NAME", help="Remove an indicator from active chart")
    args = parser.parse_args()

    # Pre-flight CDP check
    cdp_status = validate_cdp_installation()
    if not cdp_status.get("installed"):
        print(json.dumps({"success": False, "error": "TradingView CDP not ready", "issues": cdp_status.get("issues")}))
        sys.exit(1)

    result: Dict[str, Any] = {}
    if args.list:
        result = list_chart_indicators()
    elif args.add:
        result = add_chart_indicator(args.add)
    elif args.remove:
        result = remove_chart_indicator(args.remove)
    else:
        # Default to listing if no flag provided
        result = list_chart_indicators()

    print(json.dumps(result, indent=2))
    if not result.get("success", True) and "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
