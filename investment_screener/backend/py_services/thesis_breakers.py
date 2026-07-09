"""thesis_breakers.py — B5: structured, evaluated thesis breakers.

Evaluates each holding's `thesisBreakers` (target-portfolio.json) against data
`daily_brief.py` already computes this run (conviction scores, market_regime,
pillar_health) — never refetches. Breaker *definitions* stay human-owned in
target-portfolio.json (edited only via update_thesis.py's --set-breaker path);
this module owns the *evaluated state* file, data/thesis_breaker_state.json,
exclusively. See docs/superpowers/specs/2026-07-09-thesis-breakers-design.md.

Usage:
    python3 investment_screener/backend/py_services/thesis_breakers.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
STATE_PATH = DATA_DIR / "thesis_breaker_state.json"
OVERRIDES_PATH = DATA_DIR / "theses/breaker-overrides.jsonl"

AUTO_METRICS = frozenset({
    "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
})

VALID_OPERATORS = frozenset({"<", "<=", ">", ">=", "==", "in"})


def evaluate_condition(value: Any, operator: str, threshold: Any) -> bool:
    """Evaluate a single breaker condition.

    Args:
        value: Resolved metric value (may be None if unresolvable this run).
        operator: One of VALID_OPERATORS.
        threshold: Comparison value — a list when operator is "in".

    Returns:
        True if the condition is met. None values never meet a condition
        (missing data is never treated as a trigger).
    """
    if value is None:
        return False
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "==":
        return value == threshold
    if operator == "in":
        return value in threshold
    raise ValueError(f"Unknown operator: {operator!r}")


def resolve_auto_metric_value(
    metric: str,
    ticker: str,
    conviction_scores: list[dict[str, Any]],
    market_regime: dict[str, Any] | None,
    pillar_health: list[dict[str, Any]],
    target_data: dict[str, Any],
) -> Any | None:
    """Resolve an auto-metric's current value from this run's already-computed inputs.

    Never fetches new data — every value here comes from conviction_scores,
    market_regime, or pillar_health, all computed once per daily_brief.py run.

    Args:
        metric: One of AUTO_METRICS.
        ticker: Holding ticker to resolve for.
        conviction_scores: Rows from compute_conviction_scores.compute_all() (as dicts).
        market_regime: Output of market_regime.compute_market_regime(), or None if
            that step failed this run.
        pillar_health: Output of daily_brief._pillar_summary() — each entry's
            "pillar" key is the holding's subStrategyId, not pillarId.
        target_data: Parsed target-portfolio.json.

    Returns:
        The resolved value, or None if it can't be resolved this run (missing
        ticker, unavailable regime data, etc.) — never raises for missing data.

    Raises:
        ValueError: If metric is not a recognized auto metric.
    """
    if metric == "rsi":
        row = next((s for s in conviction_scores if s["ticker"] == ticker), None)
        return row["rsi"] if row else None

    if metric == "dcfFairValueGapPct":
        row = next((s for s in conviction_scores if s["ticker"] == ticker), None)
        return row["pct_to_fv"] if row else None

    if metric == "trendState":
        if not market_regime:
            return None
        tr = next((t for t in market_regime.get("tickerRegimes", []) if t["ticker"] == ticker), None)
        if not tr or not tr.get("trend"):
            return None
        return tr["trend"]["state"]

    if metric == "momentumPercentile":
        if not market_regime:
            return None
        tr = next((t for t in market_regime.get("tickerRegimes", []) if t["ticker"] == ticker), None)
        return tr["momentumPercentile"] if tr else None

    if metric == "pillarAvgScore":
        holding = next((h for h in target_data.get("holdings", []) if h["ticker"] == ticker), None)
        if not holding:
            return None
        sub_strategy = holding.get("subStrategyId")
        pillar = next((p for p in pillar_health if p["pillar"] == sub_strategy), None)
        return pillar["avg_score"] if pillar else None

    raise ValueError(f"Unknown auto metric: {metric!r} — must be one of {sorted(AUTO_METRICS)}")


def _evaluate_auto_breaker(
    breaker: dict[str, Any],
    ticker: str,
    conviction_scores: list[dict[str, Any]],
    market_regime: dict[str, Any] | None,
    pillar_health: list[dict[str, Any]],
    target_data: dict[str, Any],
    prev_entry: dict[str, Any],
    today: str,
    now_iso: str,
) -> dict[str, Any]:
    """Evaluate one auto breaker for one holding, given its prior state.

    Args:
        breaker: One entry from a holding's thesisBreakers list (type "auto").
        ticker: Holding ticker this breaker belongs to.
        conviction_scores: This run's conviction score rows (dicts).
        market_regime: This run's market_regime.compute_market_regime() output,
            or None if that step failed.
        pillar_health: This run's daily_brief._pillar_summary() output.
        target_data: Parsed target-portfolio.json.
        prev_entry: This breaker's previous state entry, or {} if none exists yet.
        today: ISO date string for today (wall-clock-free, injected).
        now_iso: ISO timestamp string for "now" (wall-clock-free, injected).

    Returns:
        The new state entry for this breaker: currentValue, conditionMet,
        currentStreak, streakStartDate, lastEvaluatedAt, and status.
    """
    value = resolve_auto_metric_value(
        breaker["metric"], ticker, conviction_scores, market_regime, pillar_health, target_data
    )
    condition_met = evaluate_condition(value, breaker["operator"], breaker["threshold"])
    prev_streak = prev_entry.get("currentStreak", 0)

    if condition_met:
        new_streak = prev_streak + 1
        streak_start = prev_entry.get("streakStartDate") if prev_streak > 0 else today
    else:
        new_streak = 0
        streak_start = None

    horizon = breaker["horizon"]
    if new_streak >= horizon:
        status = "TRIGGERED"
    elif new_streak > 0:
        status = "WATCHING"
    else:
        status = "OK"

    return {
        "type": "auto",
        "currentValue": value,
        "conditionMet": condition_met,
        "currentStreak": new_streak,
        "streakStartDate": streak_start,
        "lastEvaluatedAt": now_iso,
        "status": status,
    }


def _evaluate_manual_breaker(breaker: dict[str, Any], today: str) -> dict[str, Any]:
    """Pass through a manual breaker's hand-set status, computing staleness.

    Args:
        breaker: One entry from a holding's thesisBreakers list (type "manual").
            Must carry status, statusSetAt, and reviewCadenceDays.
        today: ISO date string for today (wall-clock-free, injected).

    Returns:
        The state entry for this breaker: status, statusSetAt, reviewCadenceDays,
        daysSinceReview, and stale.
    """
    status_set_at = date.fromisoformat(breaker["statusSetAt"])
    days_since = (date.fromisoformat(today) - status_set_at).days
    review_cadence = breaker["reviewCadenceDays"]
    return {
        "type": "manual",
        "status": breaker["status"],
        "statusSetAt": breaker["statusSetAt"],
        "reviewCadenceDays": review_cadence,
        "daysSinceReview": days_since,
        "stale": days_since > review_cadence,
    }


def evaluate_breakers(
    target_data: dict[str, Any],
    conviction_scores: list[dict[str, Any]],
    market_regime: dict[str, Any] | None,
    pillar_health: list[dict[str, Any]],
    prev_state: dict[str, Any],
    today: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Evaluate every holding's thesisBreakers against this run's data.

    Pure function — no I/O. Auto breakers use a persisted, run-based streak
    (not calendar days): each call is "one evaluated run." Manual breakers
    pass through their hand-set status and compute a staleness flag from
    reviewCadenceDays. See spec §3.2/§3.3.

    Args:
        target_data: Parsed target-portfolio.json.
        conviction_scores: This run's conviction score rows (dicts).
        market_regime: This run's market_regime.compute_market_regime() output,
            or None if that step failed.
        pillar_health: This run's daily_brief._pillar_summary() output.
        prev_state: Previous run's {ticker: {breakerId: stateEntry}}, or {}
            on the first-ever run.
        today: ISO date string (injected, never date.today() — keeps this
            function wall-clock-free and testable).

    Returns:
        {ticker: {breakerId: stateEntry}} — the new state for every breaker
        across every holding that has thesisBreakers defined.
    """
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_state: dict[str, dict[str, dict[str, Any]]] = {}

    for holding in target_data.get("holdings", []):
        breakers = holding.get("thesisBreakers", [])
        if not breakers:
            continue
        ticker = holding["ticker"]
        ticker_state: dict[str, dict[str, Any]] = {}
        for breaker in breakers:
            prev_entry = prev_state.get(ticker, {}).get(breaker["id"], {})
            if breaker["type"] == "auto":
                ticker_state[breaker["id"]] = _evaluate_auto_breaker(
                    breaker, ticker, conviction_scores, market_regime, pillar_health,
                    target_data, prev_entry, today, now_iso,
                )
            else:
                ticker_state[breaker["id"]] = _evaluate_manual_breaker(breaker, today)
        new_state[ticker] = ticker_state

    return new_state


def main() -> None:
    """CLI entry point — placeholder until Task 3 adds compute_breaker_state()."""
    print("thesis_breakers.py: run via daily_brief.py, not standalone yet.")


if __name__ == "__main__":
    main()
