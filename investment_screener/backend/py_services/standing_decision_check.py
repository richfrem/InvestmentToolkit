"""
standing_decision_check.py — reconcile a standing decision with the valuation action.

Purpose:
    A position can carry two opinions: the automatic valuation action (TRIM, ACCUMULATE,
    ...) and a standing decision recorded earlier by the owner (HOLD_AT_TARGET, ...).
    This module says, in one place, whether they agree, and what the effective stance is
    when they do not, so no page shows "TRIM" and "HOLD" side by side unexplained.
Layer:
    Business logic (pure functions; no database, network or clock access).
Usage:
    from standing_decision_check import check_standing_decision
Key Functions:
    decision_direction(decision_type)     hold | reduce | add | wait | None
    decision_condition(decision, price, levels)   is the level named in the decision reached?
    check_standing_decision(action, held, decision, recent_trades, today)
        -> {"relation", "effective", "note", "age_days"}
Key Input Dependencies:
    investment.standing_decision_* fields and recent_trades from recommendation.py.

Policy (AGENTS rule 9: the standing decision is the anchor; valuation never silently
overrides it):
    AGREES    same direction, or a neutral valuation (MAINTAIN) with a conditional
              decision: the action stands and the decision sets the timing.
    CONFLICT  opposite directions on a held position: effective stance is MAINTAIN until
              the owner resolves it; neither a buy nor a sell is proposed.
    CONFIRMED the same disagreement, but the owner set the decision within CONFIRMED_DAYS:
              the stance is theirs (MAINTAIN) and they are not asked again until it ages.
    WAITS     valuation would start a position but the decision says wait: WATCHLIST.
    OUTDATED  an entry or watchlist decision on a position that is already held: it cannot
              govern the position, so the action stands and the decision is flagged.
    UNCLEAR   the decision type cannot be read: the action stands, review asked.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

# The stored type is free text; its leading word carries the direction.
_DIRECTION_BY_PREFIX = (
    (("HOLD", "MAINTAIN", "NO_ADD"), "hold"),
    (("TRIM", "EXIT", "SELL", "REDUCE"), "reduce"),
    (("ACCUMULATE", "INITIATE", "BUY", "ADD"), "add"),
    (("WATCHLIST", "WAIT", "AWAIT", "AVOID", "MONITOR"), "wait"),
)
_ACTION_DIRECTION = {"TRIM": "reduce", "EXIT": "reduce", "ACCUMULATE": "add", "INITIATE": "add",
                     "MAINTAIN": "hold", "WATCHLIST": "wait"}
_DATE_IN_SOURCE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# A decision set this recently is the owner's current answer, not an open question.
CONFIRMED_DAYS = 30
# "Tested" for a moving average: price within this fraction above it, or below it.
EMA_TEST_BAND = 0.02
_PRICE_CONDITION = re.compile(r"_(BELOW|UNDER|ABOVE|OVER)_(\d+)(?:_(\d+))?$")
_EMA_CONDITION = re.compile(r"(?<!\d)(\d{2,3})_?EMA")
_DOLLARS_AFTER_EMA = re.compile(r"EMA[^$]{0,20}\$\s?(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)


def decision_direction(decision_type: str | None) -> str | None:
    """Which way a standing decision points, read from its leading word."""
    text = str(decision_type or "").upper()
    for prefixes, direction in _DIRECTION_BY_PREFIX:
        if any(text == prefix or text.startswith(prefix + "_") for prefix in prefixes):
            return direction
    return None


def _age_days(source: str | None, today: date) -> int | None:
    """Days since the date written in the decision's source ("user 2026-06-21"), if any."""
    match = _DATE_IN_SOURCE.search(str(source or ""))
    try:
        return (today - date.fromisoformat(match.group(1))).days if match else None
    except ValueError:
        return None


def decision_condition(decision: dict | None, price: float | None,
                       levels: dict | None = None) -> dict[str, Any] | None:
    """Check the price level a standing decision names against the current price.

    Args:
        decision: {"type", "reason", "source"} or None.
        price: Current price.
        levels: Chart levels when available, e.g. {"ema200": 48.6}.

    Returns:
        None when the decision names no readable level, else {"kind": below|above|ema,
        "label", "level", "level_source": decision|chart, "met", "distance_pct", "note"}.
        A moving average counts as reached within EMA_TEST_BAND above it. When the chart
        level is not supplied, the dollar figure written in the decision's reason is used
        and the note says so.
    """
    if not decision or not price or price <= 0:
        return None
    kind_text, reason = str(decision.get("type") or "").upper(), str(decision.get("reason") or "")
    price_match, ema_match = _PRICE_CONDITION.search(kind_text), _EMA_CONDITION.search(kind_text)
    source = "decision"
    if price_match:
        kind = "below" if price_match.group(1) in ("BELOW", "UNDER") else "above"
        level = float(f"{price_match.group(2)}.{price_match.group(3) or 0}")
        label = f"${level:,.2f} level"
    elif ema_match:
        kind, period = "ema", ema_match.group(1)
        chart = (levels or {}).get(f"ema{period}")
        written = _DOLLARS_AFTER_EMA.search(reason)
        if chart:
            level, source = float(chart), "chart"
        elif written:
            level = float(written.group(1).replace(",", ""))
        else:
            return None
        label = f"{period} EMA (${level:,.2f}{', as recorded in your decision' if source == 'decision' else ''})"
    else:
        return None
    distance = round((price - level) / level * 100, 1)
    met = price >= level if kind == "above" else price <= level * (1 + (EMA_TEST_BAND if kind == "ema" else 0))
    side = "above" if distance > 0 else "below"
    where = f"${price:,.2f} is {abs(distance):.1f}% {side} your {label}" if distance else f"${price:,.2f} is at your {label}"
    note = f"Price {where}: " + ("your condition is met." if met else "your condition is not met yet.")
    return {"kind": kind, "label": label, "level": level, "level_source": source, "met": met,
            "distance_pct": distance, "note": note}


def _traded_against(direction: str | None, recent: dict | None) -> str:
    """Sentence noting a recent trade that goes against a hold-type decision."""
    if direction != "hold" or not recent or not recent.get("count"):
        return ""
    last = (recent.get("last") or {}).get("date")
    for verb, shares in (("sold", recent.get("sold_shares") or 0), ("bought", recent.get("bought_shares") or 0)):
        if shares:
            return (f" Since then you {verb} {shares:g} share{'' if shares == 1 else 's'} on or before {last}, "
                    "so this decision looks out of date.")
    return ""


def check_standing_decision(action: str | None, held: bool, decision: dict | None,
                            recent_trades: dict | None, today: date) -> dict[str, Any]:
    """Reconcile the valuation action with the owner's standing decision.

    Args:
        action: Canonical action from recommend().
        held: True when shares are held.
        decision: {"type", "reason", "source"} or None.
        recent_trades: recent_trades summary for the ticker, or None.
        today: Date used to age the decision.

    Returns:
        {"relation": NONE|AGREES|CONFLICT|CONFIRMED|WAITS|OUTDATED|UNCLEAR, "effective": action to
        show as the stance, "note": plain explanation, "age_days": int | None}.
    """
    if not decision:
        return {"relation": "NONE", "effective": action, "note": "", "age_days": None}
    kind = str(decision.get("type") or "USER")
    label = kind.replace("_", " ").lower()
    direction, wanted = decision_direction(kind), _ACTION_DIRECTION.get(str(action))
    age = _age_days(decision.get("source"), today)
    when = f" (set {age} days ago)" if age is not None else ""
    if direction is None:
        relation, effective = "UNCLEAR", action
        note = f"Standing decision '{label}'{when} cannot be compared with {action}; review it."
    elif held and direction == "wait":
        relation, effective = "OUTDATED", action
        note = (f"Standing decision '{label}'{when} is an entry call, but you already hold this position, "
                f"so it no longer applies. The valuation action {action} stands; replace or clear the decision.")
    elif direction == wanted:
        relation, effective = "AGREES", action
        note = f"Standing decision '{label}'{when} agrees with {action}; it sets the timing."
    elif held and wanted == "hold":
        relation, effective = "AGREES", action
        note = (f"Valuation is neutral ({action}); your standing decision '{label}'{when} "
                f"decides when to act.")
    elif not held and wanted == "add" and direction in ("wait", "hold"):
        relation, effective = "WAITS", "WATCHLIST"
        note = f"Valuation says {action}, but your standing decision '{label}'{when} says wait. Stance: wait for your condition."
    elif not held:
        relation, effective = "AGREES", action
        note = f"Standing decision '{label}'{when} noted; nothing is held, so {action} stands."
    elif age is not None and 0 <= age <= CONFIRMED_DAYS:
        relation, effective = "CONFIRMED", "MAINTAIN"
        note = (f"You decided '{label}' {'today' if age == 0 else f'{age} days ago'}, so the stance is hold "
                f"and no trade is proposed. The valuation model disagrees (it reads {action}); "
                f"that is kept for your next review.")
    else:
        relation, effective = "CONFLICT", "MAINTAIN"
        note = (f"Valuation says {action}, but your standing decision is '{label}'{when}. They disagree, so the "
                f"stance is hold and no trade is proposed until you update one of them.")
    if relation in ("CONFLICT", "UNCLEAR"):
        note += _traded_against(direction, recent_trades)
    return {"relation": relation, "effective": effective, "note": note, "age_days": age}
