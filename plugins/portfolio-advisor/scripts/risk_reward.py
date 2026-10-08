"""
risk_reward.py — canonical reward-versus-risk and valuation-support view.

Purpose:
    One implementation of "is the upside worth the downside at today's price"
    and "how well supported is this fair value", attached to every canonical
    recommendation record. It informs and cross-checks the action; it never
    changes it.
Layer:
    Business logic (pure functions; no database, network or clock access).
Usage:
    from risk_reward import assess_risk_reward, valuation_support, reduce_view
Key Functions:
    assess_risk_reward(price, fair_value, scenarios)   premium, reward:risk, loss odds, verdict
    valuation_support(saved_at, analytics_log, scenarios, today)   four evidence checks
    reduce_view(held, action, assessment, current, target)   reduce flag and action alignment
Key Input Dependencies:
    Saved projection fair value, scenario prices and weights, and analytics log
    (rate audit, review readiness) supplied by recommendation.py.

Definitions:
    premium_pct      price above (+) or below (-) the saved fair value.
    reward_risk      probability-weighted gain / probability-weighted loss across
                     the saved bear, base and bull values at today's price.
    loss_odds_pct    scenario probability sitting below today's price.
    Verdict bands:   below 1 UNFAVOURABLE, 1 to under 2 THIN, 2 or more FAVOURABLE.
                     A price above fair value is always UNFAVOURABLE.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

STALE_DAYS = 90
MAX_SCENARIO_SPREAD = 50.0
UNFAVOURABLE_BELOW = 1.0
THIN_BELOW = 2.0
SCENARIO_NAMES = ("bear", "base", "bull")
REVIEW_FLAGS = ("NEEDS_REVALUATION", "UNVERIFIED_SOURCE")
BUY_ACTIONS = ("ACCUMULATE", "INITIATE")


def _number(value: Any) -> float | None:
    """Return a finite float, or None for missing, boolean or non-finite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _priced_scenarios(scenarios: dict | None) -> dict[str, tuple[float, float]] | None:
    """Return {name: (price, normalised weight)} only when all three are usable."""
    rows = {}
    for name in SCENARIO_NAMES:
        entry = (scenarios or {}).get(name) or {}
        price, weight = _number(entry.get("price")), _number(entry.get("weight"))
        if price is None or weight is None or weight <= 0:
            return None
        rows[name] = (price, weight)
    total = sum(weight for _, weight in rows.values())
    return {name: (price, weight / total) for name, (price, weight) in rows.items()}


def _verdict(premium: float, reward_risk: float | None, rated: bool, no_downside: bool) -> str:
    """Classify reward versus risk; a price above fair value needs no scenarios."""
    if premium > 0 or (reward_risk is not None and reward_risk < UNFAVOURABLE_BELOW):
        return "UNFAVOURABLE"
    if not rated:
        return "UNRATED"
    if no_downside or reward_risk >= THIN_BELOW:
        return "FAVOURABLE"
    return "THIN"


def assess_risk_reward(price: Any, fair_value: Any, scenarios: dict | None) -> dict[str, Any]:
    """Measure today's price against the saved fair value and scenario range.

    Args:
        price: Price the recommendation was computed against.
        fair_value: Saved probability-weighted fair value.
        scenarios: {"bear"|"base"|"bull": {"price": present value, "weight": probability}}.

    Returns:
        premium_pct, reward_risk, expected_gain_pct, expected_loss_pct, loss_odds_pct,
        downside_to_bear_pct, upside_to_bull_pct, no_modelled_downside and verdict.
        Unknown measures are None; nothing is estimated from partial scenarios.
    """
    price, fair_value = _number(price), _number(fair_value)
    result: dict[str, Any] = dict.fromkeys((
        "premium_pct", "reward_risk", "expected_gain_pct", "expected_loss_pct",
        "loss_odds_pct", "downside_to_bear_pct", "upside_to_bull_pct"))
    result.update(no_modelled_downside=False, verdict="UNRATED")
    if price is None or price <= 0 or fair_value is None or fair_value <= 0:
        return result
    result["premium_pct"] = (price / fair_value - 1) * 100
    priced = _priced_scenarios(scenarios)
    reward_risk = None
    if priced:
        gain = sum(weight * max(value - price, 0) for value, weight in priced.values())
        loss = sum(weight * max(price - value, 0) for value, weight in priced.values())
        reward_risk = gain / loss if loss > 0 else None
        result.update(
            reward_risk=reward_risk, no_modelled_downside=loss == 0,
            expected_gain_pct=gain / price * 100, expected_loss_pct=loss / price * 100,
            loss_odds_pct=sum(weight for value, weight in priced.values() if value < price) * 100,
            downside_to_bear_pct=(priced["bear"][0] - price) / price * 100,
            upside_to_bull_pct=(priced["bull"][0] - price) / price * 100)
    result["verdict"] = _verdict(result["premium_pct"], reward_risk, bool(priced), result["no_modelled_downside"])
    return result


def _age_days(saved_at: str | None, today: date) -> int | None:
    """Whole days since the valuation was saved; None when the date is unusable."""
    try:
        return (today - datetime.fromisoformat(str(saved_at).replace("Z", "+00:00")).date()).days
    except (TypeError, ValueError):
        return None


def _scenario_check(scenarios: dict | None) -> tuple[bool, str]:
    """Scenarios must be complete, ordered and inside the review spread limit."""
    priced = _priced_scenarios(scenarios)
    if not priced:
        return False, "Bear, base and bull values with probabilities are not all saved"
    bear, base, bull = (priced[name][0] for name in SCENARIO_NAMES)
    if not bear < base < bull:
        return False, "Scenario values are not ordered bear < base < bull"
    if bear <= 0 or bull / bear > MAX_SCENARIO_SPREAD:
        return False, f"Bull is more than {MAX_SCENARIO_SPREAD:.0f}x bear; the range is too wide to rely on"
    return True, "Bear, base and bull saved with probabilities"


def _forward_check(analytics_log: dict) -> tuple[bool, str]:
    """A recorded forward review that is not flagged for revaluation."""
    model = analytics_log.get("valuationModel") or {}
    outlook = analytics_log.get("outlookAudit") or {}
    flag = next((value for value in (model.get("readiness"), outlook.get("reviewReadiness"))
                 if value in REVIEW_FLAGS), None)
    if flag:
        return False, f"Flagged {flag}: forward assumptions are not fully verified"
    if not model and not outlook:
        return False, "No forward-earnings review recorded with this valuation"
    return True, "Forward-earnings review recorded"


def valuation_support(saved_at: str | None, analytics_log: dict | None,
                      scenarios: dict | None, today: date) -> dict[str, Any]:
    """Score the evidence behind a saved fair value on four independent checks.

    Args:
        saved_at: ISO timestamp of the saved projection (None when there is none).
        analytics_log: Saved analytics log (rate audit, readiness, outlook audit).
        scenarios: Saved scenario prices and weights.
        today: Date used for the age check.

    Returns:
        {"level": STRONG|PARTIAL|WEAK|NONE, "score", "max", "age_days", "checks": [...]}.
    """
    if saved_at is None:
        return {"level": "NONE", "score": 0, "max": 4, "age_days": None, "checks": []}
    log = analytics_log or {}
    age = _age_days(saved_at, today)
    fresh = age is not None and age <= STALE_DAYS
    audited = bool((log.get("valuationModel") or {}).get("discountRateAudit"))
    scenario_ok, scenario_note = _scenario_check(scenarios)
    forward_ok, forward_note = _forward_check(log)
    checks = [
        {"id": "fresh", "label": "Recent valuation", "ok": fresh,
         "note": "Saved date unknown" if age is None else f"Saved {age} days ago"
                 + ("" if fresh else f"; older than {STALE_DAYS} days")},
        {"id": "scenarios", "label": "Scenario range", "ok": scenario_ok, "note": scenario_note},
        {"id": "rate_audit", "label": "Audited discount rate", "ok": audited,
         "note": "Rate audit saved" if audited else "No audited discount rate; rate basis unverified"},
        {"id": "forward_review", "label": "Forward-earnings review", "ok": forward_ok, "note": forward_note},
    ]
    score = sum(check["ok"] for check in checks)
    level = "STRONG" if score == 4 else "PARTIAL" if score >= 2 else "WEAK"
    return {"level": level, "score": score, "max": 4, "age_days": age, "checks": checks}


# (actions, verdict) pairs the scenarios do not support, with the status and wording to show.
_MISALIGNED = (
    (BUY_ACTIONS, "UNFAVOURABLE", "CONFLICT", "{action} but {text}: expected loss outweighs expected gain"),
    (BUY_ACTIONS, "THIN", "REVIEW", "{action} with only thin support ({text})"),
    (("TRIM",), "FAVOURABLE", "CONFLICT", "TRIM but {text}: scenarios favour holding"),
    (("MAINTAIN",), "UNFAVOURABLE", "REVIEW",
     "MAINTAIN but {text}: inside the action band, yet upside no longer covers the risk"),
)


def _ratio_text(assessment: dict) -> str:
    """Short description of reward versus risk for notes."""
    if assessment["no_modelled_downside"]:
        return "no modelled downside"
    ratio = assessment["reward_risk"]
    return f"reward:risk {ratio:.1f}" if ratio is not None else "price above fair value"


def _alignment(action: str | None, assessment: dict) -> dict[str, str]:
    """Say whether the canonical action agrees with reward versus risk."""
    verdict, text = assessment["verdict"], _ratio_text(assessment)
    if verdict == "UNRATED":
        return {"status": "UNKNOWN", "note": "Not enough saved valuation data to cross-check the action"}
    for actions, bad_verdict, status, note in _MISALIGNED:
        if action in actions and verdict == bad_verdict:
            return {"status": status, "note": note.format(action=action, text=text)}
    return {"status": "ALIGNED", "note": f"{action or 'No action'} agrees with {text}"}


def _reduce_reasons(assessment: dict, gap: float | None) -> list[str]:
    """Plain reasons a held position is a reduce candidate; target weight is context only."""
    premium, ratio, odds = assessment["premium_pct"], assessment["reward_risk"], assessment["loss_odds_pct"]
    reasons = []
    if premium is not None and premium > 0:
        reasons.append(f"{premium:.0f}% above fair value")
    if ratio is not None:
        reasons.append(f"reward:risk {ratio:.1f} (expected gain {assessment['expected_gain_pct']:.0f}% "
                       f"vs expected loss {assessment['expected_loss_pct']:.0f}%)")
    if odds is not None:
        reasons.append(f"{odds:.0f}% of scenario probability is below today's price")
    if gap is not None and gap > 0:
        reasons.append(f"{gap:.1f}pp over target weight")
    return reasons


def reduce_view(held: bool, action: str | None, assessment: dict,
                current_weight_pct: float | None, target_weight_pct: float | None) -> dict[str, Any]:
    """Flag held positions whose reward no longer covers the risk, and check the action.

    Target weight only adds context to the reasons; it never creates the flag.
    """
    current, target = _number(current_weight_pct), _number(target_weight_pct)
    gap = round(current - target, 2) if held and current is not None and target is not None else None
    candidate = bool(held) and assessment["verdict"] == "UNFAVOURABLE"
    return {"reduce_candidate": candidate, "reduce_reasons": _reduce_reasons(assessment, gap) if candidate else [],
            "weight_gap_pp": gap, "alignment": _alignment(action, assessment)}
