#!/usr/bin/env python3
"""
tv_trades_import.py (CLI)
=====================================

Purpose:
    Import executed trades from TradingView's broker panel ("Order history" >
    "Filled", every account) into the trade_log_entry table of domain_model.sqlite.
    This is the default way the toolkit learns what was actually traded; it needs
    only TradingView Desktop with the broker connected. Trades another source
    already recorded are recognised and not duplicated.

Layer: Backend / Brokerage Automation

Usage Examples:
    # Preview what would be imported:
    python3 plugins/tradingview/scripts/tv_trades_import.py --dry-run

    # Import (JSON report for callers such as the Trade Log page):
    python3 plugins/tradingview/scripts/tv_trades_import.py --json

    # Import from a saved getOrderHistoryAllAccounts() snapshot instead of the live app:
    python3 plugins/tradingview/scripts/tv_trades_import.py --payload temp/tv_order_history.json

CLI Arguments:
    --payload            Saved order-history snapshot (default: read the live app)
    --db-path            Path to domain_model.sqlite
    --dry-run            Report what would be imported without writing
    --allow-new-symbols  Create investments for symbols the database does not know
    --json               Print the report as JSON

Key Functions:
    - fetch_tv_order_history()  - Calls getOrderHistoryAllAccounts() in broker_data.js
    - trades_from_tv_history()  - Maps filled orders to the shared trade contract
    - main()                    - CLI entry point

Script Dependencies:
    - tradingview-cdp/core/broker_data.js (getOrderHistoryAllAccounts export)
    - investment_screener/backend/py_services/trade_log_import.py (validation, de-duplication, writes)
    - TradingView Desktop running with --remote-debugging-port=9222

Notes:
    The panel's "Update Time" is when the order last changed. For a market order
    that is the fill; for a limit order it can be when the order was placed, so a
    limit order's trade date may be the placement day and no time is stored.

Exit codes: 0 success, 1 TradingView unavailable or unreadable, 2 some trades rejected.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from trade_log_import import import_filled_trades  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")
SOURCE = "tradingview"
# US and Canadian equity markets both trade on Eastern time; the trade date is an Eastern date.
MARKET_TZ = ZoneInfo("America/New_York")


def fetch_tv_order_history() -> dict:
    """Read filled orders for every account from the live TradingView broker panel."""
    from tv_client import run_node_module

    js = """
import { getOrderHistoryAllAccounts } from './core/broker_data.js';
try {
    const data = await getOrderHistoryAllAccounts();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return run_node_module(js, timeout=90)


def fetch_complete_order_history(db_path: str = _DEFAULT_DB_PATH) -> tuple[dict, list[str]]:
    """Read order history, re-reading until every account that holds something is covered.

    Returns:
        (snapshot, missing_accounts); an account that errored counts as missing
        (tv_account_coverage.py, the rule shared with the position snapshot).
    """
    from tv_account_coverage import accounts_with_holdings, read_until_complete

    conn = initialize_db(db_path)
    try:
        expected = accounts_with_holdings(conn)
    finally:
        conn.close()
    return read_until_complete(
        fetch_tv_order_history,
        lambda snap: [a.get("accountType") for a in snap.get("accounts") or [] if not a.get("error")],
        expected,
    )


def _eastern(iso: str | None) -> datetime | None:
    """Parse an ISO timestamp and express it in market (US Eastern) time."""
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(MARKET_TZ)
    except ValueError:
        return None


def trades_from_tv_history(snapshot: dict) -> tuple[list[dict], list[str]]:
    """Map filled TradingView orders to the shared trade contract.

    Returns:
        (trades, warnings). Accounts that could not be read, short reads and
        orders without a usable time are reported as warnings, never guessed.
    """
    trades: list[dict] = []
    warnings: list[str] = []
    for account in snapshot.get("accounts") or []:
        name = str(account.get("accountType") or "UNKNOWN").upper()
        if account.get("error"):
            warnings.append(f"{name}: {account['error']}")
            continue
        if account.get("missingColumns"):
            warnings.append(f"{name}: order history is missing columns {account['missingColumns']}")
            continue
        filled = [o for o in account.get("orders") or [] if o.get("status") == "filled" and (o.get("filledQty") or 0) > 0]
        expected = account.get("expectedCount")
        if expected is not None and expected != len(filled):
            warnings.append(f"{name}: read {len(filled)} filled orders but the panel shows expected {expected}")
        for order in filled:
            when = _eastern(order.get("updateTimeIso"))
            if when is None:
                warnings.append(f"{name}: {order.get('symbol')} order {order.get('orderId')} has no usable time; skipped")
                continue
            trade = {"account": name, "symbol": order.get("symbol"), "side": order.get("side"),
                     "shares": order.get("filledQty"), "price": order.get("avgFillPrice"),
                     "date": when.date().isoformat(), "orderId": order.get("orderId"),
                     "orderType": order.get("type"), "limitPrice": order.get("limitPrice")}
            if order.get("type") == "market":
                trade["executedAt"] = when.isoformat()
            trades.append(trade)
    return trades, warnings


def main() -> None:
    """CLI entry point: import executed trades from TradingView."""
    parser = argparse.ArgumentParser(description="Import executed trades from TradingView's order history")
    parser.add_argument("--payload", help="Saved order-history snapshot (default: read the live app)")
    parser.add_argument("--db-path", default=_DEFAULT_DB_PATH, help="Path to domain_model.sqlite")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be imported without writing")
    parser.add_argument("--allow-new-symbols", action="store_true",
                        help="Create investments for symbols the database does not know (default: reject them)")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args()

    missing: list[str] = []
    try:
        if args.payload:
            snapshot = json.loads(Path(args.payload).read_text())
        else:
            snapshot, missing = fetch_complete_order_history(args.db_path)
    except Exception as error:  # noqa: BLE001 - any failure to reach TradingView is reported, not raised
        snapshot = {"error": str(error)}
    if snapshot.get("error") or "accounts" not in snapshot:
        message = snapshot.get("error") or "TradingView returned no account data"
        print(json.dumps({"error": message, "source": SOURCE}) if args.json else f"Error: {message}",
              file=sys.stdout if args.json else sys.stderr)
        sys.exit(1)

    trades, warnings = trades_from_tv_history(snapshot)
    if missing:
        # Importing is additive, so the accounts that were read are still imported.
        warnings.append(f"TradingView did not return {', '.join(missing)}; trades in "
                        f"{'that account' if len(missing) == 1 else 'those accounts'} were not checked. Run the import again.")
    conn = initialize_db(args.db_path)
    try:
        report = import_filled_trades(conn, trades, source=SOURCE, dry_run=args.dry_run,
                                      allow_new_symbols=args.allow_new_symbols)
    finally:
        conn.close()
    report.update(source=SOURCE, warnings=warnings, read=len(trades), incomplete_accounts=missing)
    if args.dry_run:
        report["would_import"] = report.pop("imported")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        count = report.get("would_import", report.get("imported"))
        print(f"{'Would import' if args.dry_run else 'Imported'} {count} trade(s) from TradingView; "
              f"added details to {report['enriched']}; skipped {report['skipped']} already in the log; "
              f"rejected {len(report['rejected'])}.")
        for line in warnings + [item["reason"] for item in report["rejected"]]:
            print(f"  note: {line}", file=sys.stderr)
    sys.exit(2 if report["rejected"] or missing else 0)


if __name__ == "__main__":
    main()
