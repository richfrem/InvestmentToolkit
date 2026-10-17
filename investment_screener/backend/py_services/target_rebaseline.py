"""
target_rebaseline.py - Keep target weights current: re-baseline on trades, flag stale targets.

Purpose:
    A target weight goes stale when the owner trades without changing it: a sold position keeps
    its target and a position the owner keeps buying stays at an old target. A trade is the
    owner's freshest sizing decision, so a fill
    newer than the target's ``target_set_at`` resets that target to the post-trade weight; a
    position sold to zero gets 0%. Untraded targets stay as set and the CASH_USD target absorbs
    the difference so targets still sum to 100% (TARGET_WEIGHT_INVARIANT); only when that would
    need a negative cash target are the untraded targets scaled down to fit. Targets nobody
    traded are otherwise never overwritten: ``target_staleness()`` flags those that are old or predate the latest
    valuation, for the owner to keep or change.

    A position whose price was missed by the latest price refresh is not re-baselined (its weight
    would be wrong) and is reported instead.

Layer: Backend / Python Services (domain model consumers).

Key Functions:
    - plan_rebaseline(): the target changes a sync's new fills call for (no writes)
    - apply_rebaseline(): write a plan through update_investment_fields + one change-log entry
    - target_staleness(): why a target needs review, or None

Key Input Dependencies: investment, account_investment, investment_price, trade_log_entry,
    projection_version (domain_model.sqlite); portfolio_io.compute_weights.
Key Output Dependencies: investment.target_weight / target_set_at, portfolio_change_log.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from domain_model.investment_repository import update_investment_fields
from domain_model.portfolio_change_log_repository import record_change
from domain_model.portfolio_repository import load_portfolio_state_from_db
from portfolio_io import compute_weights

CASH_PREFIX = "CASH_"
CASH_SYMBOL = "CASH_USD"
# Reasons for a target change the owner did not decide; those keep their own target_set_at.
DERIVED = ("scaled down to fit 100%", "absorbs the change so targets sum to 100%")
# Fills inside this window count for a target that predates target_set_at (NULL).
UNSTAMPED_WINDOW_DAYS = 30
# A price this much older than the newest refreshed price was missed by that refresh.
PRICE_MISSED_HOURS = 12
STALE_TARGET_DAYS = 30


def _parse(ts: str | None) -> datetime | None:
    """Parse an ISO timestamp or YYYY-MM-DD date (taken as midnight UTC) to an aware datetime."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _missed_price_symbols(conn: sqlite3.Connection, symbols: set[str], held: set[str]) -> set[str]:
    """Which of ``symbols`` the latest price refresh missed: the newest price across all
    held positions marks that refresh, so a fixed age would flag every price on a Monday."""
    rows = conn.execute(
        "SELECT i.symbol, ip.fetched_at FROM investment i "
        "LEFT JOIN investment_price ip ON ip.investment_id = i.investment_id"
    ).fetchall()
    fetched = {sym: _parse(at) for sym, at in rows if sym in held | symbols}
    newest = max((at for at in fetched.values() if at), default=None)
    if newest is None:
        return set(symbols)
    cutoff = newest - timedelta(hours=PRICE_MISSED_HOURS)
    return {sym for sym in symbols if not fetched.get(sym) or fetched[sym] < cutoff}


def fills_since_target(conn: sqlite3.Connection, now: datetime | None = None,
                       side: str | None = None) -> set[str]:
    """Symbols with a filled trade newer than their target_set_at (or, for a target with no
    recorded date, inside the last UNSTAMPED_WINDOW_DAYS). ``side`` limits to "buy" or "sell".

    The one answer to "has the owner traded this since the target was set?", shared by the
    re-baseline, the role sync and the news-sweep prompt so none of them can call a position
    the owner just bought an exit.
    """
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(days=UNSTAMPED_WINDOW_DAYS)
    set_at = {sym: _parse(ts) for sym, ts in conn.execute(
        "SELECT symbol, target_set_at FROM investment").fetchall() if sym}
    out: set[str] = set()
    for sym, action, trade_date in conn.execute(
        "SELECT i.symbol, lower(t.action), t.trade_date FROM trade_log_entry t "
        "JOIN investment i ON i.investment_id = t.investment_id WHERE lower(t.status) = 'filled'"
    ).fetchall():
        if sym not in set_at or (side and action != side):
            continue
        filled_at = _parse(trade_date)
        if filled_at and filled_at > (set_at[sym] or window_start):
            out.add(sym)
    return out


def plan_rebaseline(conn: sqlite3.Connection, now: datetime | None = None) -> dict[str, Any]:
    """Work out which targets the latest fills reset, without writing anything.

    Returns:
        {"changes": [{symbol, investment_id, old, new, reason}], "skipped": [{symbol, reason}],
         "total_before", "total_after"} -- ``changes`` covers traded symbols, the CASH_USD
         target that absorbs the difference, and any untraded target scaled down to fit;
         empty when no fill is newer than its target.
    """
    now = now or datetime.now(timezone.utc)
    state = load_portfolio_state_from_db(conn)
    weights = compute_weights(state["shares"], state["prices"], state["total_usd"])

    rows = conn.execute(
        "SELECT investment_id, symbol, target_weight, target_set_at FROM investment"
    ).fetchall()
    every = {sym: {"investment_id": inv_id, "target": tw or 0.0, "set_at": _parse(set_at)}
             for inv_id, sym, tw, set_at in rows if sym}
    investments = {sym: inv for sym, inv in every.items() if not sym.startswith(CASH_PREFIX)}
    cash = every.get(CASH_SYMBOL)

    traded = fills_since_target(conn, now) & set(investments)

    held = {sym for sym, qty in state["shares"].items() if qty > 0}
    missed = _missed_price_symbols(conn, traded & held, held)
    skipped = [{"symbol": sym, "reason": "price missed by the latest refresh"} for sym in sorted(missed)]
    reset = {sym: (weights.get(sym, 0.0) if sym in held else 0.0) for sym in traded - missed}

    total_before = sum(inv["target"] for inv in investments.values()) + (cash["target"] if cash else 0.0)
    changes: list[dict[str, Any]] = []
    if not reset:
        return {"changes": changes, "skipped": skipped,
                "total_before": round(total_before, 4), "total_after": round(total_before, 4)}

    # Untraded targets stay exactly as set (rescaling them would invent drift the owner never
    # chose); the cash target absorbs the difference so targets still sum to 100%. Only when
    # that would need a negative cash target are the untraded targets scaled down to fit.
    others = {sym: inv["target"] for sym, inv in investments.items() if sym not in reset and inv["target"] > 0}
    room = 100.0 - sum(reset.values())
    scale = room / sum(others.values()) if sum(others.values()) > room else 1.0
    new_targets = {**reset, **{sym: old * scale for sym, old in others.items()}}
    if room <= 0:
        # Traded weights alone exceed 100% (cash below zero): normalise them.
        new_targets = {sym: w / sum(reset.values()) * 100.0 for sym, w in reset.items()}
        new_targets.update({sym: 0.0 for sym in others})
    cash_new = max(0.0, 100.0 - sum(new_targets.values()))

    for sym, new in sorted(new_targets.items()):
        old = investments[sym]["target"]
        if sym in reset:
            reason = "traded since target was set" if sym in held else "sold to zero"
        else:
            reason = "scaled down to fit 100%"
        if round(new, 4) != round(old, 4):
            changes.append({"symbol": sym, "investment_id": investments[sym]["investment_id"],
                            "old": round(old, 4), "new": round(new, 4), "reason": reason})
    if cash is not None and round(cash_new, 4) != round(cash["target"], 4):
        changes.append({"symbol": CASH_SYMBOL, "investment_id": cash["investment_id"],
                        "old": round(cash["target"], 4), "new": round(cash_new, 4),
                        "reason": "absorbs the change so targets sum to 100%"})

    total_after = sum(new_targets.values()) + (cash_new if cash is not None else 0.0)
    return {"changes": changes, "skipped": skipped,
            "total_before": round(total_before, 4), "total_after": round(total_after, 4)}


def apply_rebaseline(conn: sqlite3.Connection, plan: dict[str, Any]) -> int:
    """Write a plan's target changes and record one change-log entry. Returns rows written."""
    if not plan["changes"]:
        return 0
    stamp = datetime.now(timezone.utc).isoformat()
    for c in plan["changes"]:
        if c["reason"] in DERIVED:
            update_investment_fields(conn, c["investment_id"], target_weight=c["new"],
                                     target_set_at=_existing_set_at(conn, c["investment_id"]))
        else:
            update_investment_fields(conn, c["investment_id"], target_weight=c["new"], target_set_at=stamp)
    reset = [c for c in plan["changes"] if c["reason"] not in DERIVED]
    note = "Targets re-baselined to post-trade weights: " + ", ".join(
        f"{c['symbol']} {c['old']:.2f}%→{c['new']:.2f}%" for c in reset
    ) + f" (untraded targets kept; cash target absorbs the difference; total {plan['total_after']:.2f}%)."
    record_change(conn, note)
    return len(plan["changes"])


def _existing_set_at(conn: sqlite3.Connection, investment_id: str) -> str | None:
    row = conn.execute("SELECT target_set_at FROM investment WHERE investment_id = ?;", (investment_id,)).fetchone()
    return row[0] if row else None


def target_staleness(target_set_at: str | None, valued_at: str | None,
                     now: datetime | None = None) -> str | None:
    """Why a target needs the owner's review, or None when it is current.

    A target is stale when it has no recorded set date, is older than STALE_TARGET_DAYS, or was
    set before the latest valuation (the thesis may have moved since).
    """
    now = now or datetime.now(timezone.utc)
    set_at = _parse(target_set_at)
    if set_at is None:
        return "no record of when this target was set"
    age = (now - set_at).days
    if age > STALE_TARGET_DAYS:
        return f"target set {age} days ago"
    valued = _parse(valued_at)
    if valued and valued > set_at:
        return f"valuation updated {valued.date()} after the target was set {set_at.date()}"
    return None


def load_target_meta(conn: sqlite3.Connection, now: datetime | None = None) -> dict[str, dict[str, Any]]:
    """{symbol: {targetSetAt, staleReason}} for every investment, using its latest valuation date."""
    rows = conn.execute(
        "SELECT i.symbol, i.target_set_at, MAX(COALESCE(p.analyzed_at, p.saved_at)) "
        "FROM investment i LEFT JOIN projection_version p ON p.investment_id = i.investment_id "
        "GROUP BY i.investment_id"
    ).fetchall()
    return {sym: {"targetSetAt": set_at, "staleReason": target_staleness(set_at, valued_at, now)}
            for sym, set_at, valued_at in rows if sym}
