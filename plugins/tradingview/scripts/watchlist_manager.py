#!/usr/bin/env python3
"""
watchlist_manager.py — Synchronizes TradingView watchlists.
Reads researched watchlists (projections / watchlist.json) and active portfolio holdings,
then calls the Node.js CDP CLI to sync them to TradingView.
"""

import sys
import json
import argparse
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_PATH = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
TARGET_WATCHLIST_PATH = REPO_ROOT / "investment_screener/backend/data/watchlist.json"
PROJECTIONS_DIR = REPO_ROOT / "investment_screener/backend/data/projections"

sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))
from tv_client import tv_call, is_tv_running

def load_researched_watchlist() -> list[str]:
    """Retrieve full list of researched symbols."""
    # 1. Fallback to reading projections dir if watchlist.json doesn't exist yet
    if TARGET_WATCHLIST_PATH.exists():
        try:
            with open(TARGET_WATCHLIST_PATH) as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(s).upper() for s in data if s and s != "USD_CASH"]
                elif isinstance(data, dict) and "tickers" in data:
                    return [str(s).upper() for s in data["tickers"] if s and s != "USD_CASH"]
        except Exception:
            pass

    # Fallback to projections directory
    if PROJECTIONS_DIR.exists():
        tickers = []
        for p in PROJECTIONS_DIR.glob("*.json"):
            name = p.stem
            if name != "target-portfolio" and name != "portfolio":
                tickers.append(name.upper())
        return sorted(tickers)
    return []

def load_holdings_watchlist() -> list[str]:
    """Retrieve symbols representing active portfolio holdings."""
    if PORTFOLIO_PATH.exists():
        try:
            with open(PORTFOLIO_PATH) as f:
                data = json.load(f)
                holdings = data.get("holdings", [])
                return [h["symbol"].upper() for h in holdings if h.get("symbol") and h["symbol"] != "USD_CASH"]
        except Exception:
            pass
    return []

def run_sync(dry_run: bool = False) -> dict:
    """Execute dry-run check or actual watchlist update."""
    researched_list = load_researched_watchlist()
    holdings_list = load_holdings_watchlist()

    # Standardize Purpose HISA convention
    def normalize(s: str) -> str:
        return "PSU-U" if s in ("PSU-U.TO", "PSU.U.TO") else s

    researched_list = sorted(list(set(normalize(s) for s in researched_list)))
    holdings_list = sorted(list(set(normalize(s) for s in holdings_list)))

    actions = {
        "TA-Full Watchlist": {
            "target_count": len(researched_list),
            "tickers": researched_list
        },
        "TA-Current Holdings": {
            "target_count": len(holdings_list),
            "tickers": holdings_list
        }
    }

    if dry_run:
        return {"success": True, "actions": actions, "dry_run": True}

    if not is_tv_running():
        return {"success": False, "error": "TradingView Desktop is not running on debug port 9222"}

    # Actual sync execution via Node CLI calls
    for list_name, meta in actions.items():
        try:
            # Create list
            tv_call("watchlist", "create", list_name)
            tv_call("watchlist", "open", list_name)

            # Get current symbols in watchlist
            tv_get = tv_call("watchlist", "get")
            current_symbols = [normalize(item["symbol"].upper()) for item in tv_get.get("items", [])]

            # Sync entries
            for ticker in meta["tickers"]:
                if ticker not in current_symbols:
                    tv_call("watchlist", "add", list_name, ticker)
            for ticker in current_symbols:
                if ticker not in meta["tickers"]:
                    tv_call("watchlist", "remove", list_name, ticker)
        except Exception as e:
            return {"success": False, "error": f"Failed syncing {list_name}: {e}"}

    return {"success": True, "actions": actions, "dry_run": False}

def main():
    parser = argparse.ArgumentParser(description="Manage TradingView Watchlists")
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="Synchronize watchlists")
    sync_parser.add_argument("--dry-run", action="store_true", help="Print planned sync actions without executing")

    args = parser.parse_args()

    if args.command == "sync":
        res = run_sync(dry_run=args.dry_run)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success") else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
