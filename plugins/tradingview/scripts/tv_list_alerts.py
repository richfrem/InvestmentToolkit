#!/usr/bin/env python3
"""
tv_list_alerts.py - Fetch, analyze, and persist the active alerts currently set in TradingView.

Purpose:
    Fetch, analyze, and persist the active alerts currently set in TradingView.
Key Input Dependencies:
    None (reads live state from TradingView Desktop on port 9222 via CDP)
Key Output Dependencies:
    investment_screener/backend/data/tradingview_alerts_actual.json
Usage:
    python3 tv_list_alerts.py
"""

import sys
import json
import argparse
from pathlib import Path

def _find_scripts_dir() -> Path:
    """
    Locate the scripts directory containing tv_client.py.
    
    Walks up from the current script location to resolve import paths.
    """
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation.")

sys.path.insert(0, str(_find_scripts_dir()))
from tv_client import TV_NODE_DIR, tv_call, is_tv_running

REPO_ROOT = TV_NODE_DIR.parent
OUTPUT_FILE = REPO_ROOT / "investment_screener" / "backend" / "data" / "tradingview_alerts_actual.json"

def fetch_active_alerts() -> list[dict]:
    """Fetch active alerts from TradingView via CDP."""
    if not is_tv_running():
        print("TradingView Desktop is not running on port 9222. Cannot fetch alerts.", file=sys.stderr)
        sys.exit(1)

    try:
        # Call the Node CDP alert list command with filtering enabled
        result = tv_call("alert", "list", "--filter")
        if isinstance(result, dict) and "alerts" in result:
            return result["alerts"]
        elif isinstance(result, list):
            return result
        return []
    except Exception as e:
        print(f"Error calling TradingView alert list: {e}", file=sys.stderr)
        return []

def main():
    """
    Main execution routine for fetching and saving active alerts.
    
    Parses CLI arguments, retrieves the alerts list, persists it to disk,
    and displays a console summary table.
    """
    parser = argparse.ArgumentParser(description="Fetch and analyze active TradingView alerts.")
    parser.parse_args()

    print("Fetching active alerts from TradingView...", file=sys.stderr)
    alerts = fetch_active_alerts()
    
    # Persist alerts to local JSON file
    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(alerts, f, indent=2)
        print(f"Saved {len(alerts)} alerts to {OUTPUT_FILE}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to save alerts to disk: {e}", file=sys.stderr)

    # Print summary of the alerts
    if not alerts:
        print("\nNo active alerts found in TradingView.", file=sys.stderr)
        return

    print("\nActive TradingView Alerts Summary:")
    print(f"{'Ticker':<12} {'Price':<12} {'Condition':<15} {'Label/Message'}")
    print("-" * 75)
    for alert in sorted(alerts, key=lambda x: x.get("symbol", "")):
        symbol = alert.get("symbol", "N/A")
        price = alert.get("price", alert.get("value", "N/A"))
        condition = alert.get("condition", "crossing")
        cond_str = condition.get("type", "crossing") if isinstance(condition, dict) else str(condition)
        message = alert.get("message", alert.get("label", ""))
        
        # Standardize format for display
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else str(price)
        print(f"{symbol:<12} {price_str:<12} {cond_str:<15} {message[:35]}")

if __name__ == "__main__":
    main()
