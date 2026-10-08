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
     "trades":     [{"accountId", "symbol", "side": "buy"|"sell", "shares", "price",
                     "date": "YYYY-MM-DD", "externalId"?, "grossAmount"?}]}

Key Functions (Index):
    - trades_from_activities(): Map raw Questrade "Trades" activity rows to the trade contract.
    - normalize_trade()   : Validate one trade and build its trade_log_entry row, or return a rejection reason.
    - entry_id_for()      : Stable id so the same fill always maps to the same row.
    - import_trades()     : Write new filled rows; skip existing ones; collect rejections.
    - main()              : CLI entry point (--payload, --db-path, --dry-run, --json).

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (trade_log_entry, account, investment)
    - plugins/questrade/scripts/questrade_sync.py (canonical TFSA/RRSP account mapping)
"""

import argparse
import hashlib
import json
import math
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(_HERE))

from ticker_aliases import normalize_ticker  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.trade_log_entry_repository import get_trade_log_entry, upsert_trade_log_entry  # noqa: E402
from questrade_sync import _resolve_canonical_account_ids  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")
SOURCE = "questrade"
FILLED = "filled"
SIDES = ("buy", "sell")


def _positive_number(value: Any, allow_zero: bool = False) -> Optional[float]:
    """Finite number above zero (or zero when allowed); anything else is None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value) if value > 0 or (allow_zero and value == 0) else None


def entry_id_for(account: str, symbol: str, trade: dict) -> str:
    """Stable trade-log id: the broker's own id when present, else the fill's details."""
    external = trade.get("externalId")
    key = f"id|{external}" if external else "|".join(
        str(part) for part in (account, symbol, trade["date"], trade["side"], trade["shares"], trade["price"]))
    return "qt-" + hashlib.sha1(key.encode()).hexdigest()[:16]


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


def normalize_trade(trade: Any, account_ids: dict[str, str]) -> tuple[Optional[dict], str]:
    """Validate one trade and return (row fields, "") or (None, reason).

    Args:
        trade: One payload trade in the documented contract.
        account_ids: Questrade account uuid -> canonical account id (TFSA, RRSP, ...).
    """
    if not isinstance(trade, dict):
        return None, "trade is not an object"
    account = account_ids.get(str(trade.get("accountId")))
    if not account or account == "UNKNOWN":
        return None, f"unknown account {trade.get('accountId')!r}"
    symbol = normalize_ticker(str(trade.get("symbol") or "").strip())
    if not symbol:
        return None, "missing symbol"
    side = str(trade.get("side") or "").lower()
    if side not in SIDES:
        return None, f"side must be buy or sell, got {trade.get('side')!r}"
    shares, price = _positive_number(trade.get("shares")), _positive_number(trade.get("price"), allow_zero=True)
    if shares is None:
        return None, "shares must be a positive number"
    if price is None:
        return None, "price must be a number"
    try:
        trade_date = date.fromisoformat(str(trade.get("date"))).isoformat()
    except ValueError:
        return None, f"date must be YYYY-MM-DD, got {trade.get('date')!r}"
    clean = {**trade, "side": side, "shares": shares, "price": price, "date": trade_date}
    # The broker's own gross amount is kept when reported; otherwise shares x price.
    gross = _positive_number(trade.get("grossAmount"), allow_zero=True)
    return {"account_id": account, "symbol": symbol, "action": side, "shares": shares, "price": price,
            "trade_date": trade_date, "total_cost": gross if gross is not None else round(shares * price, 2),
            "entry_id": entry_id_for(account, symbol, clean)}, ""


def import_trades(conn: sqlite3.Connection, accounts: list[dict], trades: list[dict],
                  dry_run: bool = False) -> dict[str, Any]:
    """Write new executed trades as filled trade-log rows.

    Existing rows (same stable id) are skipped untouched, so a re-import is safe
    and owner edits survive. Rejected trades are returned with reasons.

    Returns:
        {"imported", "skipped", "rejected": [{"trade", "reason"}], "entries": [new entry ids]}.
        With dry_run, nothing is written and "imported" counts what would be.
    """
    account_ids = _resolve_canonical_account_ids(accounts)
    now = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {"imported": 0, "skipped": 0, "rejected": [], "entries": []}
    seen: set[str] = set()
    for trade in trades:
        row, reason = normalize_trade(trade, account_ids)
        if row is None:
            report["rejected"].append({"trade": trade, "reason": reason})
            continue
        if row["entry_id"] in seen or get_trade_log_entry(conn, row["entry_id"]):
            report["skipped"] += 1
            continue
        seen.add(row["entry_id"])
        report["imported"] += 1
        report["entries"].append(row["entry_id"])
        if dry_run:
            continue
        upsert_account(conn, row["account_id"], row["account_id"], row["account_id"])
        upsert_trade_log_entry(conn, {
            "entry_id": row["entry_id"], "investment_id": resolve_investment(conn, row["symbol"]),
            "account_id": row["account_id"], "action": row["action"], "shares": row["shares"],
            "price": row["price"], "total_cost": row["total_cost"],
            "order_type": None, "limit_price": None, "trade_date": row["trade_date"],
            "notes": "Executed trade imported from Questrade", "status": FILLED, "source": SOURCE,
            "priority": None, "logged_at": now, "tv_order_id": None,
        })
    return report


def main() -> None:
    """CLI entry point: import a staged Questrade trades payload."""
    parser = argparse.ArgumentParser(description="Import executed Questrade trades into the SQLite trade log")
    parser.add_argument("--payload", required=True, help="JSON file with accounts and trades")
    parser.add_argument("--db-path", default=_DEFAULT_DB_PATH, help="Path to domain_model.sqlite")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be imported without writing")
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
        report = import_trades(conn, data.get("accounts", []), trades, dry_run=args.dry_run)
    finally:
        conn.close()
    if args.dry_run:
        report["would_import"] = report.pop("imported")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        count = report.get("would_import", report.get("imported"))
        print(f"{'Would import' if args.dry_run else 'Imported'} {count} trade(s); "
              f"skipped {report['skipped']} already in the log; rejected {len(report['rejected'])}.")
        for item in report["rejected"]:
            print(f"  rejected: {item['reason']}", file=sys.stderr)
    sys.exit(2 if report["rejected"] else 0)


if __name__ == "__main__":
    main()
