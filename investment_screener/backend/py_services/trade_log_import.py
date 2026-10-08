"""
trade_log_import.py — broker-neutral import of executed trades into the trade log.

Purpose:
    One implementation for writing executed (filled) trades to the trade_log_entry
    table, whichever broker connection reported them. TradingView is the baseline
    source; Questrade is an optional second one. The same fill reported by both is
    recognised and stored once.
Layer:
    Business logic over the domain_model repositories (no network, no broker calls).
Usage:
    from trade_log_import import import_filled_trades
    report = import_filled_trades(conn, trades, source="tradingview", dry_run=True)
Key Functions:
    normalize_trade(trade)        validate one trade, or return a rejection reason
    entry_id_for(source, row, trade)  stable id so one fill always maps to one row
    import_filled_trades(...)     write new fills, add missing details, skip known ones
Key Input Dependencies:
    domain_model.sqlite (trade_log_entry, account, investment).

Trade contract (one dict per executed trade):
    account      canonical account id ("TFSA", "RRSP", "CASH"); required
    symbol, side ("buy"|"sell"), shares (> 0), price (>= 0), date ("YYYY-MM-DD")
    externalId   broker's id for the posted trade, when it has one
    orderId      broker's order id, when known (stored in tv_order_id)
    grossAmount  broker's own total, when reported (else shares x price)
    orderType    "market" | "limit" | "stop" | "stoplimit"
    limitPrice   for limit orders
    executedAt   ISO timestamp with offset; kept only when it falls on `date`

The saved trade_date is the trade date, or the ISO order time when one is known
("2026-10-06T11:49:05-04:00"); its first ten characters are always the trade date.

Same-fill rule (so two sources never double-count):
    1. the same stable id, or the same order id, is the same trade;
    2. otherwise a saved fill in the same account with the same symbol, side,
       shares and price, within MATCH_WINDOW_DAYS, and no conflicting order id;
    3. several incoming orders at one price whose shares add up to one saved
       trade are that trade (brokers post one trade for a multi-order fill).
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from domain_model.account_repository import upsert_account
from domain_model.investment_repository import get_investment, resolve_investment
from domain_model.trade_log_entry_repository import (
    get_trade_log_entry, list_filled_trades_since, upsert_trade_log_entry,
)
from ticker_aliases import normalize_ticker

FILLED = "filled"
SIDES = ("buy", "sell")
ORDER_TYPES = ("market", "limit", "stop", "stoplimit")
ID_PREFIXES = {"questrade": "qt-", "tradingview": "tv-"}
MATCH_WINDOW_DAYS = 5
PRICE_TOLERANCE = 1e-4
SHARE_TOLERANCE = 1e-6
ENRICHABLE = ("order_type", "limit_price", "tv_order_id")


def _positive_number(value: Any, allow_zero: bool = False) -> Optional[float]:
    """Finite number above zero (or zero when allowed); anything else is None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value) if value > 0 or (allow_zero and value == 0) else None


def entry_id_for(source: str, row: dict, trade: dict) -> str:
    """Stable trade-log id: the broker's trade id, else its order id, else the fill's details."""
    reference = trade.get("externalId") or trade.get("orderId")
    key = f"id|{reference}" if reference else "|".join(
        str(row[part]) for part in ("account_id", "symbol", "day", "action", "shares", "price"))
    return ID_PREFIXES.get(source, f"{source[:2]}-") + hashlib.sha1(key.encode()).hexdigest()[:16]


def _order_fields(trade: dict, day: str) -> dict[str, Any]:
    """Optional order id, type, limit and timestamp; anything unusable is left out, never guessed."""
    stamp = day
    try:
        executed = datetime.fromisoformat(str(trade.get("executedAt")))
        # Trust the time only when it falls on the broker's own trade date.
        if executed.tzinfo and executed.date().isoformat() == day:
            stamp = executed.isoformat()
    except ValueError:
        pass
    return {"order_type": trade.get("orderType") if trade.get("orderType") in ORDER_TYPES else None,
            "limit_price": _positive_number(trade.get("limitPrice")),
            "tv_order_id": str(trade["orderId"]) if trade.get("orderId") else None, "trade_date": stamp}


def normalize_trade(trade: Any) -> tuple[Optional[dict], str]:
    """Validate one trade and return (row fields, "") or (None, reason)."""
    if not isinstance(trade, dict):
        return None, "trade is not an object"
    account = str(trade.get("account") or "").upper()
    if not account or account == "UNKNOWN":
        return None, f"unknown account {trade.get('accountRef', trade.get('account'))!r}"
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
        day = date.fromisoformat(str(trade.get("date"))).isoformat()
    except ValueError:
        return None, f"date must be YYYY-MM-DD, got {trade.get('date')!r}"
    gross = _positive_number(trade.get("grossAmount"), allow_zero=True)
    return {"account_id": account, "symbol": symbol, "action": side, "shares": shares, "price": price, "day": day,
            # The broker's own gross amount is kept when reported; otherwise shares x price.
            "total_cost": gross if gross is not None else round(shares * price, 2), **_order_fields(trade, day)}, ""


def _missing_details(existing: dict, row: dict) -> dict[str, Any]:
    """Order details the saved row lacks and this import can supply; never overwrites a saved value."""
    gained = {column: row[column] for column in ENRICHABLE if existing.get(column) is None and row[column] is not None}
    saved = str(existing.get("trade_date") or "")
    if len(saved) == 10 and len(row["trade_date"]) > 10 and row["trade_date"].startswith(saved):
        gained["trade_date"] = row["trade_date"]
    return gained


def _days_apart(first: str, second: str) -> int:
    return abs((date.fromisoformat(first[:10]) - date.fromisoformat(second[:10])).days)


def _same_position(existing: dict, row: dict) -> bool:
    """Same account, symbol, side and price, close in time, with no conflicting order id."""
    return (existing["account_id"] == row["account_id"] and existing["symbol"] == row["symbol"]
            and str(existing["action"]).lower() == row["action"]
            and math.isclose(existing["price"] or 0, row["price"], abs_tol=PRICE_TOLERANCE)
            and _days_apart(str(existing["trade_date"]), row["day"]) <= MATCH_WINDOW_DAYS)


def _find_saved_fill(saved: list[dict], claimed: set[str], row: dict) -> Optional[dict]:
    """The saved fill this incoming trade refers to, or None when it is new."""
    by_id = next((e for e in saved if e["entry_id"] == row["entry_id"]), None)
    if by_id:
        return by_id
    if row["tv_order_id"]:
        by_order = next((e for e in saved if e.get("tv_order_id") == row["tv_order_id"]), None)
        if by_order:
            return by_order
    return next((e for e in saved if e["entry_id"] not in claimed and _same_position(e, row)
                 and math.isclose(e["shares"] or 0, row["shares"], abs_tol=SHARE_TOLERANCE)
                 and e.get("tv_order_id") in (None, row["tv_order_id"])), None)


def _covered_by_one_saved_trade(pending: list[dict], saved: list[dict], claimed: set[str]) -> set[int]:
    """Indexes of pending orders that together make up one saved trade (a multi-order fill)."""
    groups: dict[tuple, list[int]] = {}
    for index, row in enumerate(pending):
        groups.setdefault((row["account_id"], row["symbol"], row["action"], round(row["price"], 4)), []).append(index)
    covered: set[int] = set()
    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        total = sum(pending[i]["shares"] for i in indexes)
        whole = next((e for e in saved if e["entry_id"] not in claimed and e.get("tv_order_id") is None
                      and _same_position(e, pending[indexes[0]])
                      and math.isclose(e["shares"] or 0, total, abs_tol=SHARE_TOLERANCE)), None)
        if whole:
            claimed.add(whole["entry_id"])
            covered.update(indexes)
    return covered


def _write_new(conn: sqlite3.Connection, row: dict, source: str, now: str) -> None:
    upsert_account(conn, row["account_id"], row["account_id"], row["account_id"])
    upsert_trade_log_entry(conn, {
        "entry_id": row["entry_id"], "investment_id": resolve_investment(conn, row["symbol"]),
        "account_id": row["account_id"], "action": row["action"], "shares": row["shares"], "price": row["price"],
        "total_cost": row["total_cost"], "order_type": row["order_type"], "limit_price": row["limit_price"],
        "trade_date": row["trade_date"], "notes": f"Executed trade imported from {source.capitalize()}",
        "status": FILLED, "source": source, "priority": None, "logged_at": now, "tv_order_id": row["tv_order_id"],
    })


def _saved_fills(conn: sqlite3.Connection, rows: list[dict]) -> list[dict]:
    """Saved fills near the incoming trade dates, plus any saved row sharing an incoming id."""
    if not rows:
        return []
    earliest = min(date.fromisoformat(row["day"]) for row in rows) - timedelta(days=MATCH_WINDOW_DAYS)
    saved = list_filled_trades_since(conn, earliest.isoformat())
    known = {entry["entry_id"] for entry in saved}
    for row in rows:
        if row["entry_id"] not in known and (entry := get_trade_log_entry(conn, row["entry_id"])):
            saved.append({**entry, "symbol": row["symbol"]})
            known.add(entry["entry_id"])
    return saved


def import_filled_trades(conn: sqlite3.Connection, trades: list[dict], source: str,
                         dry_run: bool = False, allow_new_symbols: bool = False) -> dict[str, Any]:
    """Write executed trades as filled trade-log rows, once each across all sources.

    A saved fill is never re-created and its notes, status and amounts are never
    changed; it only gains order details it lacks. A symbol that is not already an
    investment is rejected unless allow_new_symbols is set, so broker-only symbols
    (cash funds, currency-conversion legs) never create investments by accident.

    Returns:
        {"imported", "skipped", "enriched", "rejected": [{"trade", "reason"}], "entries": [new ids]}.
        With dry_run, nothing is written and the counts say what would happen.
    """
    report: dict[str, Any] = {"imported": 0, "skipped": 0, "enriched": 0, "rejected": [], "entries": []}
    rows: list[dict] = []
    for trade in trades:
        row, reason = normalize_trade(trade)
        if row is not None and not allow_new_symbols and get_investment(conn, row["symbol"]) is None:
            row, reason = None, f"unknown symbol {row['symbol']}: not an investment in the portfolio database"
        if row is None:
            report["rejected"].append({"trade": trade, "reason": reason})
            continue
        row["entry_id"] = entry_id_for(source, row, trade)
        rows.append(row)

    saved, claimed, pending, seen = _saved_fills(conn, rows), set(), [], set()
    for row in rows:
        existing = None if row["entry_id"] in seen else _find_saved_fill(saved, claimed, row)
        if row["entry_id"] in seen:
            report["skipped"] += 1
        elif existing:
            claimed.add(existing["entry_id"])
            gained = _missing_details(existing, row)
            report["enriched" if gained else "skipped"] += 1
            if gained and not dry_run:
                upsert_trade_log_entry(conn, {**{k: v for k, v in existing.items() if k != "symbol"}, **gained})
        else:
            pending.append(row)
        seen.add(row["entry_id"])

    covered = _covered_by_one_saved_trade(pending, saved, claimed)
    now = datetime.now(timezone.utc).isoformat()
    for index, row in enumerate(pending):
        if index in covered:
            report["skipped"] += 1
            continue
        report["imported"] += 1
        report["entries"].append(row["entry_id"])
        if not dry_run:
            _write_new(conn, row, source, now)
    return report
