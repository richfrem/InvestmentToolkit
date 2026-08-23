#!/usr/bin/env python3
"""
tv_create_alerts.py (Python Utility)
=====================================

Purpose:
    Create and reconcile TradingView price alerts from SQLite target price levels.
    Reads fundamental price tiers (Target Entry, Buy Tiers, Sell Targets, Stop Loss,
    Fair Value) from domain_model.sqlite and compares them against live TradingView alerts
    retrieved via Chrome DevTools Protocol (CDP) on port 9222.
    Detects missing or drifted alerts and supports automated creation.

Layer: Plugins / TradingView / Scripts

Usage Examples:
    # Reconcile all tickers against live TradingView alerts:
    python3 plugins/tradingview/scripts/tv_create_alerts.py --reconcile

    # Create alerts for a specific ticker:
    python3 plugins/tradingview/scripts/tv_create_alerts.py --ticker NVDA

    # Dry run creation:
    python3 plugins/tradingview/scripts/tv_create_alerts.py --ticker NVDA --dry-run

Key Functions:
    - reconcile_alerts()      — Diffs target SQLite levels against active TV alerts with alias safety
    - get_tier_alert_levels() — Reads price_level_set / price_level_tier rows from SQLite
    - get_alert_levels()      — Extracts bear/base/bull and fair value prices from projection tables
    - create_alert()          — Submits an alert creation command to TradingView Desktop via CDP
    - process_ticker()        — Main per-ticker alert synchronization pipeline

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Price Levels & Projections)
    - tradingview-cdp/ (Node.js CDP Engine)
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")

sys.path.insert(0, str(_find_scripts_dir()))
from tv_client import TV_NODE_DIR, tv_call, is_tv_running

REPO_ROOT = TV_NODE_DIR.parent
DB_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener" / "backend" / "py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection,
    get_latest_projection_by_source,
    get_projection_scenarios,
    list_symbols_with_projections,
)
from domain_model.price_level_repository import get_price_levels  # noqa: E402
from ticker_aliases import normalize_ticker  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_exchange_prefix(symbol: str) -> str:
    """Strip exchange prefix (e.g. 'NASDAQ:NVDA' -> 'NVDA')."""
    return symbol.split(":", 1)[-1] if symbol else symbol


def load_latest_ai_entry(ticker: str, db_path: Path = DB_PATH) -> dict | None:
    """Load latest projection entry and scenarios for ticker from SQLite."""
    conn = initialize_db(str(db_path))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker.upper(),)
        ).fetchone()
        if row is None:
            return None
        investment_id = row[0]

        entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
        if entry is None:
            entry = get_latest_projection(conn, investment_id)
        if entry is None:
            return None

        scenario_rows = get_projection_scenarios(conn, entry["projection_id"])
        scenarios = {
            s["scenario_name"]: {"scenarioPrice": s.get("scenario_price")}
            for s in scenario_rows
        }

        return {
            "ticker": ticker.upper(),
            "savedAt": entry.get("saved_at", ""),
            "scenarios": scenarios,
            "aiThesis": {"fairValue": entry.get("fair_value")},
        }
    finally:
        conn.close()


def get_alert_levels(entry: dict) -> list[tuple[str, float]]:
    """Extract (label, price) tuples from a projection entry."""
    levels = []
    ticker = entry.get("ticker", "UNKNOWN")
    scenarios = entry.get("scenarios", {})

    for scenario in ("bear", "base", "bull"):
        s = scenarios.get(scenario, {})
        price = s.get("scenarioPrice")
        if price and price > 0:
            label = f"{ticker} {scenario.capitalize()} ${price:.0f}"
            levels.append((label, float(price)))

    fair_value = entry.get("aiThesis", {}).get("fairValue")
    if fair_value and fair_value > 0:
        label = f"{ticker} DCF Fair Value ${fair_value:.0f}"
        levels.append((label, float(fair_value)))

    return levels


def get_tier_alert_levels(ticker: str, db_path: Path = DB_PATH) -> list[tuple[str, float]]:
    """Extract (label, price) tuples from price_level_set / price_level_tier tables."""
    conn = initialize_db(str(db_path))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker.upper(),)
        ).fetchone()
        if row is None:
            return []
        investment_id = row[0]
        price_levels = get_price_levels(conn, investment_id)
        if not price_levels:
            return []

        levels = []
        for tier in price_levels.get("buy_tiers", []):
            price = tier.get("price")
            tier_num = tier.get("tier_number", 1)
            if price and price > 0:
                levels.append((f"{ticker} Buy Tier {tier_num} ${price:.0f}", float(price)))

        for tier in price_levels.get("sell_tiers", []):
            price = tier.get("price")
            trim_pct = tier.get("trim_pct", "")
            trim_str = f" ({trim_pct}% trim)" if trim_pct else ""
            if price and price > 0:
                levels.append((f"{ticker} Sell Target ${price:.0f}{trim_str}", float(price)))

        stop_loss = price_levels.get("stop_loss")
        sl_price = stop_loss.get("price") if isinstance(stop_loss, dict) else None
        if sl_price and sl_price > 0:
            levels.append((f"{ticker} Stop Loss ${sl_price:.0f}", float(sl_price)))

        target_entry = price_levels.get("target_entry")
        te_price = target_entry.get("price") if isinstance(target_entry, dict) else None
        if te_price and te_price > 0:
            levels.append((f"{ticker} Target Entry ${te_price:.0f}", float(te_price)))

        return levels
    finally:
        conn.close()


def create_alert(ticker: str, price: float, message: str, dry_run: bool = False):
    """Dispatch CDP alert creation call to TradingView."""
    if dry_run:
        return {"status": "dry_run", "ticker": ticker, "price": price, "message": message}

    return tv_call(
        "alert", "create",
        "--price", str(price),
        "--condition", "crossing",
        "--message", message,
    )


# ---------------------------------------------------------------------------
# Reconciliation Logic (Pitfall #18 safe)
# ---------------------------------------------------------------------------

def reconcile_alerts(target_levels: Dict[str, Dict[str, Any]], active_tv_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare SQLite target price levels against active TradingView alerts.
    Normalized for PSU-U.TO / PSU.U.TO alias safety.

    Args:
        target_levels: Dict mapping ticker to dict of level names and target prices.
        active_tv_alerts: List of active alert dicts returned from TradingView.

    Returns:
        Summary dict of matched, missing, and drifted alert records.
    """
    matched = []
    missing = []
    drifted = []

    # Map active alerts by normalized ticker
    active_by_sym: Dict[str, List[float]] = {}
    for a in active_tv_alerts:
        raw_sym = _strip_exchange_prefix(a.get("symbol", ""))
        norm_sym = normalize_ticker(raw_sym)
        p = a.get("price")
        if p is not None:
            active_by_sym.setdefault(norm_sym, []).append(float(p))

    for target_sym, levels in target_levels.items():
        norm_sym = normalize_ticker(target_sym)
        tv_prices = active_by_sym.get(norm_sym, [])

        for level_key, expected_price in levels.items():
            if expected_price is None or expected_price <= 0:
                continue

            # Check if there is an alert within 1% price tolerance
            match = next((p for p in tv_prices if abs(p - expected_price) / expected_price < 0.01), None)
            if match is not None:
                matched.append({"symbol": norm_sym, "level": level_key, "expected": expected_price, "actual": match})
            else:
                missing.append({"symbol": norm_sym, "level": level_key, "expected": expected_price})

    return {
        "matched": matched,
        "missing": missing,
        "drifted": drifted,
        "total_matched": len(matched),
        "total_missing": len(missing),
    }


def get_all_tickers(db_path: Path = DB_PATH) -> list[str]:
    """Return all tickers that have projections in SQLite."""
    conn = initialize_db(str(db_path))
    try:
        return list_symbols_with_projections(conn)
    finally:
        conn.close()


def process_ticker(ticker: str, dry_run: bool, db_path: Path = DB_PATH) -> dict:
    """Create alerts for a single ticker. Returns summary dictionary."""
    tier_levels: list[tuple[str, float]] = get_tier_alert_levels(ticker, db_path)
    entry = load_latest_ai_entry(ticker, db_path)
    dcf_levels = get_alert_levels(entry) if entry else []

    levels = tier_levels if tier_levels else dcf_levels

    if not levels:
        return {
            "ticker": ticker,
            "status": "skipped",
            "reason": "no price levels or scenarioPrice values found",
        }

    created = []
    failed = []
    for label, price in levels:
        try:
            result = create_alert(ticker, price, label, dry_run=dry_run)
        except Exception as e:
            failed.append({"label": label, "price": price, "error": str(e)})
            continue

        if isinstance(result, dict) and result.get("error"):
            failed.append({"label": label, "price": price, "error": result["error"]})
        else:
            created.append({"label": label, "price": price, "result": result})

    return {
        "ticker": ticker,
        "status": "dry_run" if dry_run else "ok",
        "alerts_created": len(created),
        "alerts_failed": len(failed),
        "details": created + failed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create or reconcile TradingView price alerts from SQLite levels."
    )
    parser.add_argument("--ticker", help="Single ticker to process (default: all)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without calling TradingView",
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Reconcile active TV alerts against target SQLite price levels",
    )
    args = parser.parse_args()

    if args.reconcile:
        print("Reconciling TradingView alerts with SQLite target levels...")
        from tv_list_alerts import list_alerts_from_tv
        active_alerts = list_alerts_from_tv() if not args.dry_run else []
        
        tickers = [args.ticker.upper()] if args.ticker else get_all_tickers()
        target_dict = {}
        for t in tickers:
            levels = {}
            for label, price in get_tier_alert_levels(t):
                levels[label] = price
            if not levels:
                entry = load_latest_ai_entry(t)
                for label, price in get_alert_levels(entry) if entry else []:
                    levels[label] = price
            if levels:
                target_dict[t] = levels

        report = reconcile_alerts(target_dict, active_alerts)
        print(json.dumps(report, indent=2))
        return

    if not args.dry_run and not is_tv_running():
        print(
            "\nTradingView Desktop not detected on port 9222.\n"
            "Launch it with:  python3 plugins/tradingview/scripts/tv_launch.py\n"
            "Or manually:     open -a TradingView --args --remote-debugging-port=9222\n",
            file=sys.stderr,
        )
        sys.exit(1)

    tickers = [args.ticker.upper()] if args.ticker else get_all_tickers()

    if not tickers:
        print(json.dumps({"error": "No projection files found"}))
        sys.exit(1)

    results = []
    for ticker in sorted(tickers):
        result = process_ticker(ticker, dry_run=args.dry_run)
        results.append(result)

    total_created = sum(r.get("alerts_created", 0) for r in results)
    total_skipped = sum(1 for r in results if r["status"] == "skipped")
    total_failed = sum(r.get("alerts_failed", 0) for r in results)

    output = {
        "results": results,
        "summary": {
            "tickers_processed": len(tickers) - total_skipped,
            "tickers_skipped": total_skipped,
            "alerts_created": total_created,
            "alerts_failed": total_failed,
            "dry_run": args.dry_run,
        },
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
