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
from datetime import datetime, timezone
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
DB_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener" / "backend" / "py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.alert_repository import upsert_alert  # noqa: E402


def _strip_exchange_prefix(symbol: str) -> str:
    """TradingView alert symbols are exchange-qualified (e.g. "NASDAQ:IREN").
    domain_model's investment.symbol is the bare ticker. Mirrors
    migrate_target_portfolio_to_sqlite.py's helper of the same name."""
    return symbol.split(":", 1)[-1] if symbol else symbol


def save_alerts_to_db(alerts: list[dict], db_path: Path = DB_PATH) -> int:
    """Persist fetched alerts via the domain-model repository (``alert`` table).

    Storage backend (Wave 2 Task 10 producer cutover): replaces writing
    tradingview_alerts_actual.json in place with ``alert_repository.upsert_alert``
    (ADR-029), one row per alert, field-mapped identically to
    ``migrate_target_portfolio_to_sqlite.py``'s original one-time migration of
    this same file.

    Returns:
        Number of alerts upserted.
    """
    conn = initialize_db(str(db_path))
    try:
        synced_at = datetime.now(timezone.utc).isoformat()
        for alert_entry in alerts:
            raw_symbol = alert_entry.get("symbol")
            ticker = _strip_exchange_prefix(raw_symbol) if raw_symbol else None
            investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD") if ticker else None
            upsert_alert(
                conn,
                alert_id=str(alert_entry.get("alert_id")),
                investment_id=investment_id,
                alert_type=alert_entry.get("type"),
                message=alert_entry.get("message"),
                price=alert_entry.get("price"),
                condition_json=json.dumps(alert_entry.get("condition")) if alert_entry.get("condition") else None,
                active=bool(alert_entry.get("active", True)),
                resolution=alert_entry.get("resolution"),
                created_at=alert_entry.get("created"),
                last_fired_at=alert_entry.get("last_fired"),
                expiration_at=alert_entry.get("expiration"),
                synced_at=synced_at,
            )
        return len(alerts)
    finally:
        conn.close()


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

    # Persist alerts via the domain-model repository (Wave 2 Task 10 producer
    # cutover) instead of rewriting tradingview_alerts_actual.json in place.
    try:
        count = save_alerts_to_db(alerts)
        print(f"Saved {count} alerts to {DB_PATH} (alert table)", file=sys.stderr)
    except Exception as e:
        print(f"Failed to save alerts to domain_model.sqlite: {e}", file=sys.stderr)

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
