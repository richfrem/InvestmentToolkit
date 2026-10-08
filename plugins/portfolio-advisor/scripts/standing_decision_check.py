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
        {"relation": NONE|AGREES|CONFLICT|WAITS|OUTDATED|UNCLEAR, "effective": action to
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
    else:
        relation, effective = "CONFLICT", "MAINTAIN"
        note = (f"Valuation says {action}, but your standing decision is '{label}'{when}. They disagree, so the "
                f"stance is hold and no trade is proposed until you update one of them.")
    if relation in ("CONFLICT", "UNCLEAR"):
        note += _traded_against(direction, recent_trades)
    return {"relation": relation, "effective": effective, "note": note, "age_days": age}
