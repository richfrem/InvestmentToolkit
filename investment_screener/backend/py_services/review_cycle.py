"""
review_cycle.py - Every followed investment is reviewed each cycle; nothing is left unanalysed.

Purpose:
    Recommendations went stale because nothing forced a look: a 7-week-old valuation kept
    producing BUY or TRIM calls, and analysis shown to the owner never reached the record.
    Each daily or weekly cycle now:
      1. start()  - resets every holding and watchlist name to NEEDS_ANALYSIS (the default for
                    a new ticker too);
      2. triage() - deterministically returns to REVIEWED only names with no reason to look
                    again, and records why the rest need analysis;
      3. mark()   - records a review of one name after analysis (refused while a hard trigger
                    stands and no valuation was saved today);
      4. verify() - lists names still NEEDS_ANALYSIS; the cycle fails while any remain.
    While a name is NEEDS_ANALYSIS, recommendation.py gives it no buy/trim call.

Triggers (why a name needs analysis):
    HARD (needs a valuation saved today): no valuation; earnings reported after the valuation's
        evidence date; price moved more than PRICE_MOVE_PCT since the last review; a TRIGGERED
        thesis breaker.
    AGE (may be marked with a written reason): valuation older than REFRESH_BEFORE_ACTING_DAYS.
    CHECK (may be marked with a written reason): the last earnings date could not be fetched.
        The recommendation still withholds buy/trim calls until it is re-valued.

Layer: Backend / Python Services (domain model consumers).
Key Functions: in_scope, start, valuation_price, triggers, triage, mark, verify, status
Key Input Dependencies: investment, account_investment, investment_price, projection_version.
Key Output Dependencies: investment.review_state / reviewed_at / review_price / review_reason /
    last_earnings_at.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterable

from domain_model.investment_repository import update_investment_fields
from ticker_aliases import is_cash_equivalent

NEEDS_ANALYSIS = "NEEDS_ANALYSIS"
REVIEWED = "REVIEWED"
STALE_DAYS = 30          # same threshold as risk_reward.REFRESH_BEFORE_ACTING_DAYS
PRICE_MOVE_PCT = 20.0
MIN_REASON_CHARS = 20


def _day(ts: str | None) -> str | None:
    return str(ts)[:10] if ts else None


def in_scope(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Holdings and watchlist names (cash excluded), with what the cycle needs about each."""
    rows = conn.execute(
        """
        SELECT i.investment_id, i.symbol, i.review_state, i.reviewed_at, i.review_price, i.last_earnings_at,
               COALESCE((SELECT SUM(a.quantity) FROM account_investment a WHERE a.investment_id = i.investment_id), 0) AS qty,
               COALESCE(i.is_watchlisted, 0) AS watch,
               (SELECT ip.price FROM investment_price ip WHERE ip.investment_id = i.investment_id) AS price
        FROM investment i
        """
    ).fetchall()
    out = []
    for inv_id, sym, state, rev_at, rev_px, last_earn, qty, watch, price in rows:
        if not sym or is_cash_equivalent(sym) or sym.startswith("CASH_") or not (qty > 0 or watch):
            continue
        out.append(dict(investment_id=inv_id, symbol=sym, state=state, reviewed_at=rev_at, review_price=rev_px,
                        last_earnings_at=last_earn, held=qty > 0, price=price))
    return out


def valuation_evidence(conn: sqlite3.Connection, investment_id: str) -> tuple[str | None, str | None]:
    """(evidence date of the preferred saved valuation, saved_at) or (None, None)."""
    row = conn.execute(
        "SELECT saved_at, analyzed_at, analytics_log_json FROM projection_version WHERE investment_id = ? "
        "ORDER BY CASE WHEN source = 'AI_AGENT' THEN 0 ELSE 1 END, saved_at DESC LIMIT 1", (investment_id,)
    ).fetchone()
    if not row:
        return None, None
    saved_at, analyzed_at, log_json = row
    try:
        log = json.loads(log_json or "{}")
    except ValueError:
        log = {}
    rebased = isinstance(log, dict) and ((log.get("valuationModel") or {}).get("rebasedFrom"))
    return (analyzed_at if rebased and analyzed_at else saved_at), saved_at


def valuation_price(conn: sqlite3.Connection, investment_id: str) -> float | None:
    """Price recorded with the preferred saved valuation, or None."""
    row = conn.execute(
        "SELECT COALESCE(json_extract(snapshot_json, '$.currentPrice'), json_extract(snapshot_json, '$.price')) "
        "FROM projection_version WHERE investment_id = ? "
        "ORDER BY CASE WHEN source = 'AI_AGENT' THEN 0 ELSE 1 END, saved_at DESC LIMIT 1", (investment_id,)
    ).fetchone()
    try:
        return float(row[0]) if row and row[0] else None
    except (TypeError, ValueError):
        return None


def triggers(item: dict[str, Any], evidence: str | None, today: date, breaker: bool,
             earnings_unknown: bool = False) -> list[tuple[str, str]]:
    """[(kind, reason)] where kind is HARD, AGE or CHECK; empty when nothing calls for a fresh look.

    CHECK: the last earnings date could not be determined, so "nothing new" can't be confirmed.
    """
    out: list[tuple[str, str]] = []
    if earnings_unknown:
        out.append(("CHECK", "last earnings date unavailable; confirm none since the valuation"))
    ev = _day(evidence)
    if not ev:
        out.append(("HARD", "no saved valuation"))
    else:
        age = (today - date.fromisoformat(ev)).days
        if item.get("last_earnings_at") and _day(item["last_earnings_at"]) > ev:
            out.append(("HARD", f"earnings reported {_day(item['last_earnings_at'])} after the valuation ({ev})"))
        if age > STALE_DAYS:
            out.append(("AGE", f"valuation is {age} days old"))
    base, since = item.get("review_price"), "the last review"
    if not base:
        base, since = item.get("valuation_price"), "the saved valuation"
    if base and item.get("price"):
        move = (item["price"] / base - 1) * 100
        if abs(move) > PRICE_MOVE_PCT:
            out.append(("HARD", f"price moved {move:+.0f}% since {since}"))
    if breaker:
        out.append(("HARD", "a thesis breaker is TRIGGERED"))
    return out


def start(conn: sqlite3.Connection) -> int:
    """Reset every holding and watchlist name to NEEDS_ANALYSIS. Returns the count."""
    names = in_scope(conn)
    for n in names:
        update_investment_fields(conn, n["investment_id"], review_state=NEEDS_ANALYSIS)
    return len(names)


def triage(conn: sqlite3.Connection, today: date | None = None,
           last_earnings: Callable[[str], str | None] | None = None,
           breakers: Iterable[str] = ()) -> list[dict[str, Any]]:
    """Clear names with no trigger; return the queue (held first, then hardest triggers first)."""
    today = today or date.today()
    breakers = set(breakers)
    now = datetime.now(timezone.utc).isoformat()
    queue = []
    for n in in_scope(conn):
        if n["state"] != NEEDS_ANALYSIS:
            continue
        earnings_unknown = False
        if last_earnings:
            try:
                le = last_earnings(n["symbol"])
            except LookupError:
                le, earnings_unknown = None, True
            if le and le != n["last_earnings_at"]:
                update_investment_fields(conn, n["investment_id"], last_earnings_at=le)
                n["last_earnings_at"] = le
        evidence, _ = valuation_evidence(conn, n["investment_id"])
        n["valuation_price"] = valuation_price(conn, n["investment_id"])
        found = triggers(n, evidence, today, n["symbol"] in breakers, earnings_unknown)
        if not found:
            update_investment_fields(conn, n["investment_id"], review_state=REVIEWED, reviewed_at=now,
                                     review_price=n["price"], review_reason=f"auto: no new facts (valuation {_day(evidence)})")
            continue
        update_investment_fields(conn, n["investment_id"], review_reason="needs analysis: " + "; ".join(r for _, r in found))
        queue.append({"symbol": n["symbol"], "held": n["held"], "hard": any(k == "HARD" for k, _ in found),
                      "reasons": [r for _, r in found]})
    queue.sort(key=lambda q: (not q["held"], not q["hard"], q["symbol"]))
    return queue


def mark(conn: sqlite3.Connection, symbol: str, reason: str, today: date | None = None,
         breakers: Iterable[str] = ()) -> dict[str, Any]:
    """Record a review of one name. Refused while a HARD trigger stands without a valuation saved today."""
    today = today or date.today()
    item = next((n for n in in_scope(conn) if n["symbol"] == symbol), None)
    if item is None:
        return {"ok": False, "symbol": symbol, "error": "not a holding or watchlist name"}
    if len((reason or "").strip()) < MIN_REASON_CHARS:
        return {"ok": False, "symbol": symbol, "error": f"reason must be at least {MIN_REASON_CHARS} characters"}
    evidence, saved_at = valuation_evidence(conn, item["investment_id"])
    item["valuation_price"] = valuation_price(conn, item["investment_id"])
    saved_today = _day(saved_at) == today.isoformat()
    hard = [r for k, r in triggers(item, evidence, today, symbol in set(breakers)) if k == "HARD"]
    if hard and not saved_today:
        return {"ok": False, "symbol": symbol, "error": "needs a valuation saved today: " + "; ".join(hard)}
    update_investment_fields(conn, item["investment_id"], review_state=REVIEWED,
                             reviewed_at=datetime.now(timezone.utc).isoformat(),
                             review_price=item["price"], review_reason=reason.strip())
    return {"ok": True, "symbol": symbol, "valuation_saved_today": saved_today}


def verify(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Names still NEEDS_ANALYSIS (the cycle is incomplete while this is non-empty)."""
    return [{"symbol": n["symbol"], "held": n["held"]} for n in in_scope(conn) if n["state"] == NEEDS_ANALYSIS]


def status(conn: sqlite3.Connection) -> dict[str, int]:
    names = in_scope(conn)
    return {"in_scope": len(names), "needs_analysis": sum(n["state"] == NEEDS_ANALYSIS for n in names),
            "reviewed": sum(n["state"] == REVIEWED for n in names)}
