#!/usr/bin/env python3
"""
questrade_trades_import.py - Import executed Questrade trades into the SQLite trade log.

Purpose:
    Writes executed trades fetched through the Questrade MCP into the
    trade_log_entry table of domain_model.sqlite as filled rows, so the Trade Log
    page and the recommendation's recent-trade context reflect what was really
    traded. Re-imports never duplicate a trade and never overwrite a row the owner
    has edited. Invalid trades are reported with a reason and never written.

Layer:
    Plugins / Questrade / Services

Usage Examples:
    # Preview what would be imported:
    python3 plugins/questrade/scripts/questrade_trades_import.py --payload temp/questrade_trades_payload.json --dry-run

    # Import:
    python3 plugins/questrade/scripts/questrade_trades_import.py --payload temp/questrade_trades_payload.json --json

Payload (either or both of "activities" and "trades"):
    {"accounts":   [list_accounts rows: {id, name, ...}],
     "activities": {accountId: [raw get_account_activities rows, transactionTypes=["Trades"]]},
     "orders":     {accountId: raw get_order_history response} (optional: adds order type, limit and time),
     "trades":     [{"accountId", "symbol", "side": "buy"|"sell", "shares", "price",
                     "date": "YYYY-MM-DD", "externalId"?, "grossAmount"?,
                     "orderType"?, "limitPrice"?, "executedAt"?: ISO timestamp on the trade date}]}

    The saved trade_date is the trade date, or the ISO order time when one is known
    ("2026-10-06T11:49:05-04:00"); its first ten characters are always the trade date.

Key Functions (Index):
    - trades_from_activities(): Map raw Questrade "Trades" activity rows to the trade contract.
    - attach_order_details(): Add order type, limit price and market-order time from get_order_history.
    - import_trades()     : Resolve Questrade accounts, then import through trade_log_import (shared core).
    - main()              : CLI entry point (--payload, --db-path, --dry-run, --json).

Key Input Dependencies:
    - investment_screener/backend/py_services/trade_log_import.py (validation, de-duplication, writes)
    - investment_screener/backend/data/domain_model.sqlite (trade_log_entry, account, investment)
    - plugins/questrade/scripts/questrade_sync.py (canonical TFSA/RRSP account mapping)
"""

import argparse
import json
import math
import sqlite3
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(_HERE))

from domain_model.db_client import initialize_db  # noqa: E402
from trade_log_import import import_filled_trades  # noqa: E402
from questrade_sync import _resolve_canonical_account_ids  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")
SOURCE = "questrade"
# US and Canadian equity markets both trade on Eastern time; the trade date is an Eastern date.
MARKET_TZ = ZoneInfo("America/New_York")


def trades_from_activities(activities: dict[str, list[dict]]) -> list[dict]:
    """Map raw get_account_activities rows to the trade contract.

    Live shape (questrade-tool-schemas.md): {transactionId, transactionType, symbol,
    quantity (negative for sells), price, tradeDate, action "Buy"|"Sell",
    gross: {amount}}. Rows that are not Trades are ignored. Values are copied, not
    derived; validation happens later in normalize_trade().
    """
    trades = []
    for account_id, rows in (activities or {}).items():
        for row in rows or []:
            if not isinstance(row, dict) or row.get("transactionType") != "Trades":
                continue
            quantity, gross = row.get("quantity"), (row.get("gross") or {}).get("amount")
            trades.append({
                "accountId": account_id, "symbol": row.get("symbol"), "side": str(row.get("action") or "").lower(),
                "shares": abs(quantity) if isinstance(quantity, (int, float)) and not isinstance(quantity, bool) else quantity,
                "price": row.get("price"), "date": row.get("tradeDate"), "externalId": row.get("transactionId"),
                "grossAmount": abs(gross) if isinstance(gross, (int, float)) and not isinstance(gross, bool) else None,
            })
    return trades


def _order_rows(orders: Any) -> list[dict]:
    """Filled orders from a get_order_history response ({"open", "history"}) or a plain list, de-duplicated."""
    rows = orders if isinstance(orders, list) else [*(orders or {}).get("history", []), *(orders or {}).get("open", [])]
    unique = {row.get("id"): row for row in rows if isinstance(row, dict) and row.get("status") == "filled"}
    return list(unique.values())


def attach_order_details(trades: list[dict], orders: dict[str, Any] | None) -> list[dict]:
    """Add order id, order type, limit price and, for market orders, the order time to matching trades.

    A trade matches a filled order in the same account with the same symbol, side,
    quantity and average price. `lastModified` is when the order was last changed,
    not when it filled, so it is used as the time only for market orders, which fill
    on submission. Each order is used once; unmatched trades are returned unchanged.
    """
    pool = {account: _order_rows(rows) for account, rows in (orders or {}).items()}
    result = []
    for trade in trades:
        candidates = pool.get(str(trade.get("accountId")), [])
        match = next((o for o in candidates
                      if str(o.get("instrument") or "").upper() == str(trade.get("symbol") or "").upper()
                      and o.get("side") == trade.get("side") and o.get("filledQty") == trade.get("shares")
                      and isinstance(o.get("avgPrice"), (int, float)) and isinstance(trade.get("price"), (int, float))
                      and math.isclose(o["avgPrice"], trade["price"], abs_tol=1e-4)), None)
        if match is None:
            result.append(trade)
            continue
        candidates.remove(match)
        extra: dict[str, Any] = {"orderType": match.get("type"), "orderId": match.get("id")}
        if match.get("limitPrice") is not None:
            extra["limitPrice"] = match["limitPrice"]
        if match.get("type") == "market" and isinstance(match.get("lastModified"), (int, float)):
            extra["executedAt"] = datetime.fromtimestamp(match["lastModified"], MARKET_TZ).isoformat()
        result.append({**trade, **extra})
    return result


def import_trades(conn: sqlite3.Connection, accounts: list[dict], trades: list[dict],
                  dry_run: bool = False, allow_new_symbols: bool = False) -> dict[str, Any]:
    """Resolve Questrade account ids to canonical accounts and import through the shared core.

    All validation, de-duplication (including against trades already imported from
    TradingView) and writing live in trade_log_import.import_filled_trades.
    """
    account_ids = _resolve_canonical_account_ids(accounts)
    resolved = [{**trade, "account": account_ids.get(str(trade.get("accountId"))), "accountRef": trade.get("accountId")}
                if isinstance(trade, dict) else trade for trade in trades]
    return import_filled_trades(conn, resolved, source=SOURCE, dry_run=dry_run, allow_new_symbols=allow_new_symbols)


def main() -> None:
    """CLI entry point: import a staged Questrade trades payload."""
    parser = argparse.ArgumentParser(description="Import executed Questrade trades into the SQLite trade log")
    parser.add_argument("--payload", required=True, help="JSON file with accounts and trades")
    parser.add_argument("--db-path", default=_DEFAULT_DB_PATH, help="Path to domain_model.sqlite")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be imported without writing")
    parser.add_argument("--allow-new-symbols", action="store_true",
                        help="Create investments for symbols the database does not know (default: reject them)")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args()

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"Error: Payload file not found at {payload_path}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(payload_path.read_text())
    conn = initialize_db(args.db_path)
    try:
        trades = trades_from_activities(data.get("activities", {})) + data.get("trades", [])
        trades = attach_order_details(trades, data.get("orders"))
        report = import_trades(conn, data.get("accounts", []), trades, dry_run=args.dry_run,
                               allow_new_symbols=args.allow_new_symbols)
    finally:
        conn.close()
    if args.dry_run:
        report["would_import"] = report.pop("imported")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        count = report.get("would_import", report.get("imported"))
        print(f"{'Would import' if args.dry_run else 'Imported'} {count} trade(s); "
              f"added details to {report['enriched']}; skipped {report['skipped']} already in the log; "
              f"rejected {len(report['rejected'])}.")
        for item in report["rejected"]:
            print(f"  rejected: {item['reason']}", file=sys.stderr)
    sys.exit(2 if report["rejected"] else 0)


if __name__ == "__main__":
    main()
