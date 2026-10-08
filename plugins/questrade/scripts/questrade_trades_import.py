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
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(_HERE))

from ticker_aliases import normalize_ticker  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment, resolve_investment  # noqa: E402
from domain_model.trade_log_entry_repository import get_trade_log_entry, upsert_trade_log_entry  # noqa: E402
from questrade_sync import _resolve_canonical_account_ids  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")
SOURCE = "questrade"
FILLED = "filled"
SIDES = ("buy", "sell")
ORDER_TYPES = ("market", "limit", "stop", "stoplimit")
# US and Canadian equity markets both trade on Eastern time; the trade date is an Eastern date.
MARKET_TZ = ZoneInfo("America/New_York")


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


def _order_rows(orders: Any) -> list[dict]:
    """Filled orders from a get_order_history response ({"open", "history"}) or a plain list, de-duplicated."""
    rows = orders if isinstance(orders, list) else [*(orders or {}).get("history", []), *(orders or {}).get("open", [])]
    unique = {row.get("id"): row for row in rows if isinstance(row, dict) and row.get("status") == "filled"}
    return list(unique.values())


def attach_order_details(trades: list[dict], orders: dict[str, Any] | None) -> list[dict]:
    """Add order type, limit price and, for market orders, the order time to matching trades.

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
        extra: dict[str, Any] = {"orderType": match.get("type")}
        if match.get("limitPrice") is not None:
            extra["limitPrice"] = match["limitPrice"]
        if match.get("type") == "market" and isinstance(match.get("lastModified"), (int, float)):
            extra["executedAt"] = datetime.fromtimestamp(match["lastModified"], MARKET_TZ).isoformat()
        result.append({**trade, **extra})
    return result


def _order_fields(trade: dict, trade_date: str) -> dict[str, Any]:
    """Optional order type, limit price and timestamp; anything unusable is left out, never guessed."""
    order_type = trade.get("orderType") if trade.get("orderType") in ORDER_TYPES else None
    stamp = trade_date
    try:
        executed = datetime.fromisoformat(str(trade.get("executedAt")))
        # Trust the time only when it falls on the broker's own trade date.
        if executed.tzinfo and executed.date().isoformat() == trade_date:
            stamp = executed.isoformat()
    except ValueError:
        pass
    return {"order_type": order_type, "limit_price": _positive_number(trade.get("limitPrice")), "trade_date": stamp}


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
            "total_cost": gross if gross is not None else round(shares * price, 2),
            "entry_id": entry_id_for(account, symbol, clean), **_order_fields(trade, trade_date)}, ""


def _missing_details(existing: dict, row: dict) -> dict[str, Any]:
    """Order details the saved row lacks and this import can supply; never overwrites a saved value."""
    gained: dict[str, Any] = {}
    for column in ("order_type", "limit_price"):
        if existing.get(column) is None and row[column] is not None:
            gained[column] = row[column]
    saved = str(existing.get("trade_date") or "")
    if len(saved) == 10 and len(row["trade_date"]) > 10 and row["trade_date"].startswith(saved):
        gained["trade_date"] = row["trade_date"]
    return gained


def import_trades(conn: sqlite3.Connection, accounts: list[dict], trades: list[dict],
                  dry_run: bool = False, allow_new_symbols: bool = False) -> dict[str, Any]:
    """Write new executed trades as filled trade-log rows.

    Existing rows (same stable id) are never re-created and their notes, status and
    amounts are never changed, so a re-import is safe and owner edits survive. An
    existing row only gains order details it does not have yet (order type, limit
    price, order time). Rejected trades are returned with reasons. A symbol that is
    not already an investment is rejected unless allow_new_symbols is set, so
    broker-only symbols (cash funds, currency-conversion legs) never create
    investments by accident.

    Returns:
        {"imported", "skipped", "enriched", "rejected": [{"trade", "reason"}], "entries": [new entry ids]}.
        With dry_run, nothing is written and the counts say what would happen.
    """
    account_ids = _resolve_canonical_account_ids(accounts)
    now = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {"imported": 0, "skipped": 0, "enriched": 0, "rejected": [], "entries": []}
    seen: set[str] = set()
    for trade in trades:
        row, reason = normalize_trade(trade, account_ids)
        if row is not None and not allow_new_symbols and get_investment(conn, row["symbol"]) is None:
            row, reason = None, f"unknown symbol {row['symbol']}: not an investment in the portfolio database"
        if row is None:
            report["rejected"].append({"trade": trade, "reason": reason})
            continue
        existing = None if row["entry_id"] in seen else get_trade_log_entry(conn, row["entry_id"])
        if existing or row["entry_id"] in seen:
            gained = _missing_details(existing, row) if existing else {}
            report["enriched" if gained else "skipped"] += 1
            if gained and not dry_run:
                upsert_trade_log_entry(conn, {**existing, **gained})
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
            "order_type": row["order_type"], "limit_price": row["limit_price"], "trade_date": row["trade_date"],
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
