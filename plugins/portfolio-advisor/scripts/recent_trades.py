"""
recent_trades.py — canonical recent-trade context for recommendations.

Purpose:
    One implementation of "what did the owner actually trade lately, and does it
    already follow the action". Attached to every canonical recommendation record
    so a TRIM that was just trimmed is shown as acted on instead of repeated as
    if nothing happened. It informs the action; it never changes it.
Layer:
    Business logic (pure functions; no database, network or clock access).
Usage:
    from recent_trades import summarize_recent_trades, trade_context
Key Functions:
    summarize_recent_trades(trades, today)   shares sold and bought inside the window, newest fill
    trade_context(action, summary)           ACTED / OPPOSED / RECENT / NONE with a plain note
Key Input Dependencies:
    Filled trade_log_entry rows (trade_log_entry_repository.list_filled_trades_since)
    supplied by recommendation.py.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

RECENT_TRADE_DAYS = 14
SELL_ACTIONS = ("TRIM", "EXIT")
BUY_ACTIONS = ("ACCUMULATE", "INITIATE")


def window_start(today: date) -> str:
    """ISO date of the first day inside the recent-trade window."""
    return (today - timedelta(days=RECENT_TRADE_DAYS)).isoformat()


def _trade_day(row: dict) -> str | None:
    """Valid ISO trade date (YYYY-MM-DD) or None."""
    try:
        return date.fromisoformat(str(row.get("trade_date"))[:10]).isoformat()
    except ValueError:
        return None


def summarize_recent_trades(trades: list[dict], today: date) -> dict[str, Any]:
    """Total filled shares per side inside the window and report the newest fill.

    Args:
        trades: Filled trade rows for one investment (repository column names).
        today: Date the window ends on.

    Returns:
        {"window_days", "sold_shares", "bought_shares", "count", "last"} where
        last is {"date", "action", "shares", "price", "account"} or None.
    """
    start = window_start(today)
    recent = [(day, row) for row in trades if (day := _trade_day(row)) and start <= day <= today.isoformat()]
    sides = {"sell": 0.0, "buy": 0.0}
    for _, row in recent:
        side = str(row.get("action") or "").lower()
        if side in sides:
            sides[side] += float(row.get("shares") or 0)
    last = None
    if recent:
        # Newest trade date wins; among fills on the same day the later row wins.
        day, row = max(enumerate(recent), key=lambda item: (item[1][0], item[0]))[1]
        last = {"date": day, "action": str(row.get("action") or "").lower(), "shares": row.get("shares"),
                "price": row.get("price"), "account": row.get("account_id")}
    return {"window_days": RECENT_TRADE_DAYS, "sold_shares": sides["sell"], "bought_shares": sides["buy"],
            "count": len(recent), "last": last}


def _shares_text(verb: str, shares: float, summary: dict) -> str:
    """'Sold 3 shares, last on 2026-10-06' with tidy number formatting."""
    amount = f"{shares:g}"
    return f"{verb} {amount} share{'' if shares == 1 else 's'} in the last {summary['window_days']} days, last on {summary['last']['date']}"


def trade_context(action: str | None, summary: dict) -> dict[str, str]:
    """Say whether recent filled trades already follow, or run against, the action.

    Returns:
        {"status": "ACTED" | "OPPOSED" | "RECENT" | "NONE", "note": str}.
    """
    if not summary["count"]:
        return {"status": "NONE", "note": ""}
    sold, bought = summary["sold_shares"], summary["bought_shares"]
    sold_text = _shares_text("Sold", sold, summary) if sold else ""
    bought_text = _shares_text("Bought", bought, summary) if bought else ""
    if action in SELL_ACTIONS and sold:
        return {"status": "ACTED", "note": f"{sold_text}: {action} already acted on"}
    if action in BUY_ACTIONS and bought:
        return {"status": "ACTED", "note": f"{bought_text}: {action} already acted on"}
    if action in SELL_ACTIONS and bought:
        return {"status": "OPPOSED", "note": f"{bought_text}, while the action is {action}"}
    if action in BUY_ACTIONS and sold:
        return {"status": "OPPOSED", "note": f"{sold_text}, while the action is {action}"}
    return {"status": "RECENT", "note": "; ".join(text for text in (sold_text, bought_text) if text)}
