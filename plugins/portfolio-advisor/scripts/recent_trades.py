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
    flip_hold_note(action, trades, today)  a reversal of a recent trade held back, or None
    trade_context(action, summary)           ACTED / OPPOSED / RECENT / NONE with a plain note
Key Input Dependencies:
    Filled trade_log_entry rows (trade_log_entry_repository.list_filled_trades_since)
    supplied by recommendation.py.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

RECENT_TRADE_DAYS = 14
# After the owner trades, a call may not reverse that trade for this long (buy -> no TRIM/EXIT,
# sell -> no ACCUMULATE/INITIATE). Only a TRIGGERED thesis breaker can override after a buy.
FLIP_HOLD_DAYS = 30
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


def flip_hold_note(action: str | None, trades: list[dict], today: date,
                   breaker_triggered: bool = False, new_evidence_date: str | None = None) -> dict | None:
    """Whether a call that reverses the owner's recent trade is held back or allowed, and why.

    Within FLIP_HOLD_DAYS of a trade, a call may not flip against it: after a buy, no TRIM/EXIT;
    after a sell, no ACCUMULATE/INITIATE. Valuation drift or a stale target alone never reverses a
    decision the owner just acted on. Only compelling new facts lift the hold: a TRIGGERED thesis
    breaker (after a buy), or a re-verified valuation whose evidence is dated after the trade.

    Returns:
        None when the call doesn't reverse a recent trade; otherwise
        {"held": True, "note": why it is held back} or {"held": False, "note": what allowed it}.
    """
    if action in SELL_ACTIONS:
        side, verb, flip = "buy", "Bought", "a buy"
    elif action in BUY_ACTIONS:
        side, verb, flip = "sell", "Sold", "a sale"
    else:
        return None
    start = (today - timedelta(days=FLIP_HOLD_DAYS)).isoformat()
    days_traded = [day for row in trades if str(row.get("action") or "").lower() == side
                   and (day := _trade_day(row)) and start <= day <= today.isoformat()]
    if not days_traded:
        return None
    last = max(days_traded)
    ago = (today - date.fromisoformat(last)).days
    if action in SELL_ACTIONS and breaker_triggered:
        return {"held": False, "note": f"{verb} on {last}, but a thesis breaker triggered: {action} allowed"}
    evidence = str(new_evidence_date or "")[:10]
    if evidence and evidence > last:
        return {"held": False, "note": (f"{verb} on {last}; reversal to {action} allowed by a re-verified "
                                        f"valuation dated {evidence}, after the trade")}
    return {"held": True, "note": (f"{verb} on {last} ({ago} days ago): {action} is held back for "
                                   f"{FLIP_HOLD_DAYS} days after {flip} unless new facts arrive (a triggered "
                                   f"thesis breaker or a re-verified valuation dated after the trade)")}


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
