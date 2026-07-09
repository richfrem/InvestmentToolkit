# Thesis Breakers (B5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the framework's "3 specific, measurable thesis breakers" from prose into
structured, evaluated data: a `thesisBreakers` schema on each holding, a CLI to author them,
an evaluation engine (`thesis_breakers.py`) that checks the automatable ones every `/daily`
run and tracks the manual ones for staleness, a triage integration that puts any `TRIGGERED`
breaker at the very top of the brief, an accountability log for overrides, and a new
interactive HITL skill (`set-thesis-breakers`) so nobody hand-authors raw breaker JSON.

**Architecture:** One new file, `investment_screener/backend/py_services/thesis_breakers.py`,
built bottom-up as pure, independently-testable functions (condition evaluation → metric
resolution → streak/staleness algorithm → I/O wrapper), then additive changes to
`update_thesis.py` (CLI) and `daily_brief.py` (integration), then a new conversational skill.
Breaker *definitions* live in `target-portfolio.json` (human-owned, via the existing
`save_thesis()` versioned/diffed path); breaker *evaluated state* lives in a new
`data/thesis_breaker_state.json` (machine-owned, rewritten every run) — mirroring how E1's
`risk_snapshot.json` and C2's embedded `market_regime` never mutate `target-portfolio.json`.

**Tech Stack:** Python 3, pytest, argparse. No new dependencies. Reuses conviction scores
(`compute_conviction_scores.py`), `market_regime.py`'s per-ticker `tickerRegimes`, and
`daily_brief.py`'s pillar-health aggregation — all already computed once per `/daily` run,
never refetched.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-09-thesis-breakers-design.md` — read it once before
  starting; every task below implements a piece of it.
- Ticker field is always `ticker`, never `symbol` (CLAUDE.md rule 10).
- `thesis_breakers.py` never mutates `target-portfolio.json`. Only `update_thesis.py` (via
  `save_thesis()`) writes to that file. `thesis_breakers.py` owns
  `data/thesis_breaker_state.json` exclusively.
- Auto-breaker streaks count **consecutive evaluated `/daily` runs**, not calendar days —
  no historical time-series store exists or is added by this plan (spec §3.2).
- A `TRIGGERED` breaker escalates visibility only — it never flips `aiThesis.action` or
  bypasses `standingDecision` (spec §4, guide §10.3).
- All new/changed Python files: file header + Google-style docstrings on every non-trivial
  function, full type hints, snake_case, refactor at 50+ lines or 3+ nesting levels
  (`.agent/rules/coding-conventions.md`).
- TDD: every function gets its failing test written first (repo's non-negotiable rule 1).
  No live network calls, no wall-clock coupling in tests — "today" is always an injected
  parameter, never `date.today()` called inside a pure function under test.
- Commit after every task.

---

## Task 1: Condition evaluation + auto-metric resolution

**Files:**
- Create: `investment_screener/backend/py_services/thesis_breakers.py`
- Test: `investment_screener/backend/tests/py_services/test_thesis_breakers.py`

**Interfaces:**
- Produces: `evaluate_condition(value: Any, operator: str, threshold: Any) -> bool`,
  `resolve_auto_metric_value(metric: str, ticker: str, conviction_scores: list[dict], market_regime: dict | None, pillar_health: list[dict], target_data: dict) -> Any | None`,
  `AUTO_METRICS: frozenset[str]` (module constant:
  `{"rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore"}`)

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for thesis_breakers.py — B5 structured thesis breaker evaluation."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from thesis_breakers import (  # noqa: E402
    AUTO_METRICS,
    evaluate_condition,
    resolve_auto_metric_value,
)


class TestEvaluateCondition:
    def test_less_than_true(self):
        assert evaluate_condition(10, "<", 20) is True

    def test_less_than_false(self):
        assert evaluate_condition(20, "<", 20) is False

    def test_less_than_or_equal_boundary(self):
        assert evaluate_condition(20, "<=", 20) is True

    def test_greater_than_true(self):
        assert evaluate_condition(30, ">", 20) is True

    def test_greater_than_or_equal_boundary(self):
        assert evaluate_condition(20, ">=", 20) is True

    def test_equals(self):
        assert evaluate_condition("DOWNTREND", "==", "DOWNTREND") is True

    def test_in_list_match(self):
        assert evaluate_condition("DOWNTREND", "in", ["DOWNTREND", "WEAKENING"]) is True

    def test_in_list_no_match(self):
        assert evaluate_condition("UPTREND", "in", ["DOWNTREND", "WEAKENING"]) is False

    def test_none_value_never_meets_condition(self):
        assert evaluate_condition(None, "<", 20) is False

    def test_unknown_operator_raises(self):
        with pytest.raises(ValueError, match="Unknown operator"):
            evaluate_condition(10, "!=", 20)


class TestResolveAutoMetricValue:
    def _inputs(self):
        conviction_scores = [
            {"ticker": "NBIS", "rsi": 28.5, "pct_to_fv": -42.3},
            {"ticker": "PANW", "rsi": 55.0, "pct_to_fv": 12.0},
        ]
        market_regime = {
            "tickerRegimes": [
                {
                    "ticker": "NBIS",
                    "trend": {"position": "BELOW", "slope": "FALLING", "state": "DOWNTREND"},
                    "momentumPercentile": 8.5,
                    "volatilityPercentile": 91.0,
                },
                {"ticker": "PANW", "trend": None, "momentumPercentile": None,
                 "volatilityPercentile": None},
            ]
        }
        pillar_health = [
            {"pillar": "asi_race", "avg_score": -1.5, "count": 3, "min": -3, "max": 1},
        ]
        target_data = {
            "holdings": [
                {"ticker": "NBIS", "subStrategyId": "asi_race", "targetWeight": 5.5},
                {"ticker": "PANW", "subStrategyId": "cybersecurity", "targetWeight": 5.9},
            ]
        }
        return conviction_scores, market_regime, pillar_health, target_data

    def test_rsi_resolves_from_conviction_scores(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value("rsi", "NBIS", scores, regime, pillars, target) == 28.5

    def test_dcf_fair_value_gap_resolves_from_pct_to_fv(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "dcfFairValueGapPct", "NBIS", scores, regime, pillars, target
        ) == -42.3

    def test_trend_state_resolves_from_market_regime(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "trendState", "NBIS", scores, regime, pillars, target
        ) == "DOWNTREND"

    def test_trend_state_none_when_trend_unavailable(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "trendState", "PANW", scores, regime, pillars, target
        ) is None

    def test_momentum_percentile_resolves(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "momentumPercentile", "NBIS", scores, regime, pillars, target
        ) == 8.5

    def test_pillar_avg_score_resolves_via_sub_strategy_id(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "pillarAvgScore", "NBIS", scores, regime, pillars, target
        ) == -1.5

    def test_missing_ticker_in_conviction_scores_returns_none(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "rsi", "UNKNOWN", scores, regime, pillars, target
        ) is None

    def test_market_regime_unavailable_returns_none(self):
        scores, _, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "trendState", "NBIS", scores, None, pillars, target
        ) is None

    def test_unknown_metric_raises(self):
        scores, regime, pillars, target = self._inputs()
        with pytest.raises(ValueError, match="Unknown auto metric"):
            resolve_auto_metric_value("madeUpMetric", "NBIS", scores, regime, pillars, target)

    def test_auto_metrics_constant_has_five_entries(self):
        assert AUTO_METRICS == frozenset({
            "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
        })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_thesis_breakers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'thesis_breakers'`

- [ ] **Step 3: Write minimal implementation**

```python
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


def main() -> None:
    """CLI entry point — placeholder until Task 3 adds compute_breaker_state()."""
    print("thesis_breakers.py: run via daily_brief.py, not standalone yet.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_thesis_breakers.py -v`
Expected: PASS (20 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/thesis_breakers.py investment_screener/backend/tests/py_services/test_thesis_breakers.py
git commit -m "feat: add condition evaluation and auto-metric resolution (B5 task 1)"
```

---

## Task 2: Streak/staleness algorithm — `evaluate_breakers()`

**Files:**
- Modify: `investment_screener/backend/py_services/thesis_breakers.py`
- Test: `investment_screener/backend/tests/py_services/test_thesis_breakers.py`

**Interfaces:**
- Consumes: `evaluate_condition`, `resolve_auto_metric_value` (Task 1)
- Produces: `evaluate_breakers(target_data: dict, conviction_scores: list[dict], market_regime: dict | None, pillar_health: list[dict], prev_state: dict, today: str) -> dict[str, dict[str, dict]]`
  — returns `{ticker: {breakerId: stateEntry}}`, the exact shape stored under
  `thesis_breaker_state.json`'s `"holdings"` key.

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_thesis_breakers.py`:

```python
from thesis_breakers import evaluate_breakers  # noqa: E402


def _target_data_one_auto_breaker(horizon: int = 5) -> dict:
    return {
        "holdings": [
            {
                "ticker": "NBIS",
                "subStrategyId": "asi_race",
                "targetWeight": 5.5,
                "thesisBreakers": [
                    {
                        "id": "nbis-trend-breakdown",
                        "type": "auto",
                        "metric": "trendState",
                        "operator": "in",
                        "threshold": ["DOWNTREND"],
                        "horizon": horizon,
                        "note": "Sustained downtrend contradicts the thesis",
                    }
                ],
            }
        ]
    }


def _regime_with_trend(state: str) -> dict:
    return {"tickerRegimes": [
        {"ticker": "NBIS", "trend": {"position": "BELOW", "slope": "FALLING", "state": state},
         "momentumPercentile": 10.0, "volatilityPercentile": 80.0},
    ]}


class TestEvaluateBreakersAutoStreak:
    def test_first_true_evaluation_starts_streak_at_one_and_watching(self):
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("DOWNTREND"),
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 1
        assert entry["conditionMet"] is True
        assert entry["status"] == "WATCHING"
        assert entry["streakStartDate"] == "2026-07-09"
        assert entry["currentValue"] == "DOWNTREND"

    def test_streak_increments_across_runs(self):
        prev_state = {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 3, "streakStartDate": "2026-07-05",
            "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
        }}}
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("DOWNTREND"),
            [], prev_state=prev_state, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 4
        assert entry["streakStartDate"] == "2026-07-05"
        assert entry["status"] == "WATCHING"

    def test_streak_reaches_horizon_becomes_triggered(self):
        prev_state = {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 4, "streakStartDate": "2026-07-05",
            "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
        }}}
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("DOWNTREND"),
            [], prev_state=prev_state, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 5
        assert entry["status"] == "TRIGGERED"

    def test_condition_false_resets_streak_to_zero(self):
        prev_state = {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 4, "streakStartDate": "2026-07-05",
            "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
        }}}
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("UPTREND"),
            [], prev_state=prev_state, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 0
        assert entry["conditionMet"] is False
        assert entry["status"] == "OK"
        assert entry["streakStartDate"] is None

    def test_unresolvable_metric_never_crashes_and_counts_as_not_met(self):
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], None,
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["conditionMet"] is False
        assert entry["currentStreak"] == 0


class TestEvaluateBreakersManualStaleness:
    def _target_data_one_manual_breaker(self, review_cadence_days: int = 90) -> dict:
        return {
            "holdings": [
                {
                    "ticker": "NBIS",
                    "subStrategyId": "asi_race",
                    "targetWeight": 5.5,
                    "thesisBreakers": [
                        {
                            "id": "nbis-ndr-floor",
                            "type": "manual",
                            "metric": "ndr",
                            "operator": "<",
                            "threshold": 115,
                            "horizon": "2 quarters",
                            "note": "NDR floor from 10-Q disclosures",
                            "status": "OK",
                            "statusSetAt": "2026-07-01",
                            "statusSetBy": "agent",
                            "reviewCadenceDays": review_cadence_days,
                        }
                    ],
                }
            ]
        }

    def test_manual_breaker_not_stale_within_cadence(self):
        result = evaluate_breakers(
            self._target_data_one_manual_breaker(review_cadence_days=90), [], None,
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-ndr-floor"]
        assert entry["daysSinceReview"] == 8
        assert entry["stale"] is False
        assert entry["status"] == "OK"

    def test_manual_breaker_stale_past_cadence(self):
        result = evaluate_breakers(
            self._target_data_one_manual_breaker(review_cadence_days=5), [], None,
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-ndr-floor"]
        assert entry["daysSinceReview"] == 8
        assert entry["stale"] is True

    def test_manual_breaker_status_passed_through_verbatim(self):
        target = self._target_data_one_manual_breaker()
        target["holdings"][0]["thesisBreakers"][0]["status"] = "TRIGGERED"
        result = evaluate_breakers(target, [], None, [], prev_state={}, today="2026-07-09")
        assert result["NBIS"]["nbis-ndr-floor"]["status"] == "TRIGGERED"


class TestEvaluateBreakersNoBreakers:
    def test_holding_with_no_thesis_breakers_produces_no_entries(self):
        target = {"holdings": [{"ticker": "MSFT", "targetWeight": 2.4}]}
        result = evaluate_breakers(target, [], None, [], prev_state={}, today="2026-07-09")
        assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_thesis_breakers.py -v`
Expected: FAIL with `ImportError: cannot import name 'evaluate_breakers'`

- [ ] **Step 3: Write minimal implementation**

Add to `investment_screener/backend/py_services/thesis_breakers.py` (after `resolve_auto_metric_value`,
before `main()`):

```python
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
    """Evaluate one auto breaker for one holding, given its prior state."""
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
    """Pass through a manual breaker's hand-set status, computing staleness."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_thesis_breakers.py -v`
Expected: PASS (32 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/thesis_breakers.py investment_screener/backend/tests/py_services/test_thesis_breakers.py
git commit -m "feat: add streak/staleness evaluation algorithm (B5 task 2)"
```

---

## Task 3: I/O wrapper + override logging

**Files:**
- Modify: `investment_screener/backend/py_services/thesis_breakers.py`
- Test: `investment_screener/backend/tests/py_services/test_thesis_breakers.py`

**Interfaces:**
- Consumes: `evaluate_breakers` (Task 2)
- Produces: `compute_breaker_state(conviction_scores, market_regime, pillar_health, target_portfolio_path=TARGET_PATH, state_path=STATE_PATH) -> tuple[dict, list[dict]]`
  (returns `(full_state_dict, triggered_list)` — `full_state_dict` has `"generatedAt"` and
  `"holdings"` keys; each item in `triggered_list` has `ticker`, `breakerId`, and every field
  from both the definition and the state entry, plus `targetWeight`),
  `log_breaker_override(ticker: str, breaker_id: str, metric: str, current_value: Any, threshold: Any, streak: int | None, horizon: Any, rationale: str, overridden_by: str = "user", path: Path = OVERRIDES_PATH) -> None`,
  `_cli_log_override(ticker: str, breaker_id: str, rationale: str, overridden_by: str = "user", target_portfolio_path: Path = TARGET_PATH, state_path: Path = STATE_PATH, overrides_path: Path = OVERRIDES_PATH) -> None`
  (resolves a breaker's definition + current state, then calls `log_breaker_override` —
  this is what the `--log-override` CLI flag calls, and what Task 7's daily-loop-agent
  wiring shells out to), plus a `--log-override` CLI mode on `main()`

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_thesis_breakers.py`:

```python
import json as _json

from thesis_breakers import (  # noqa: E402
    _cli_log_override,
    compute_breaker_state,
    log_breaker_override,
)


class TestComputeBreakerState:
    def test_writes_state_file_and_returns_triggered_list(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        state_path = tmp_path / "thesis_breaker_state.json"
        target_data = {
            "holdings": [
                {
                    "ticker": "NBIS",
                    "subStrategyId": "asi_race",
                    "targetWeight": 5.5,
                    "thesisBreakers": [
                        {
                            "id": "nbis-trend-breakdown",
                            "type": "auto",
                            "metric": "trendState",
                            "operator": "in",
                            "threshold": ["DOWNTREND"],
                            "horizon": 5,
                            "note": "Sustained downtrend",
                        }
                    ],
                },
                {"ticker": "MSFT", "subStrategyId": "quality_saas", "targetWeight": 2.4},
            ]
        }
        target_path.write_text(_json.dumps(target_data))
        prev_state = {
            "generatedAt": "2026-07-08T13:00:00Z",
            "holdings": {"NBIS": {"nbis-trend-breakdown": {
                "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
                "currentStreak": 4, "streakStartDate": "2026-07-04",
                "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
            }}},
        }
        state_path.write_text(_json.dumps(prev_state))
        market_regime = {"tickerRegimes": [
            {"ticker": "NBIS", "trend": {"position": "BELOW", "slope": "FALLING",
             "state": "DOWNTREND"}, "momentumPercentile": 5.0, "volatilityPercentile": 90.0},
        ]}

        state, triggered = compute_breaker_state(
            conviction_scores=[], market_regime=market_regime, pillar_health=[],
            target_portfolio_path=target_path, state_path=state_path,
        )

        assert state_path.exists()
        on_disk = _json.loads(state_path.read_text())
        assert on_disk["holdings"]["NBIS"]["nbis-trend-breakdown"]["status"] == "TRIGGERED"
        assert "generatedAt" in on_disk

        assert len(triggered) == 1
        assert triggered[0]["ticker"] == "NBIS"
        assert triggered[0]["breakerId"] == "nbis-trend-breakdown"
        assert triggered[0]["metric"] == "trendState"
        assert triggered[0]["targetWeight"] == 5.5
        assert triggered[0]["currentStreak"] == 5

    def test_no_prior_state_file_treated_as_empty(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        state_path = tmp_path / "thesis_breaker_state.json"
        target_path.write_text(_json.dumps({"holdings": []}))

        state, triggered = compute_breaker_state(
            conviction_scores=[], market_regime=None, pillar_health=[],
            target_portfolio_path=target_path, state_path=state_path,
        )

        assert state["holdings"] == {}
        assert triggered == []


class TestLogBreakerOverride:
    def test_appends_one_jsonl_line(self, tmp_path):
        path = tmp_path / "breaker-overrides.jsonl"
        log_breaker_override(
            ticker="NBIS", breaker_id="nbis-trend-breakdown", metric="trendState",
            current_value="DOWNTREND", threshold=["DOWNTREND"], streak=5, horizon=5,
            rationale="Vera Rubin ramp de-risks the downtrend; holding through",
            path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = _json.loads(lines[0])
        assert entry["ticker"] == "NBIS"
        assert entry["breakerId"] == "nbis-trend-breakdown"
        assert entry["overriddenBy"] == "user"
        assert "date" in entry

    def test_second_call_appends_not_overwrites(self, tmp_path):
        path = tmp_path / "breaker-overrides.jsonl"
        log_breaker_override(
            ticker="NBIS", breaker_id="a", metric="rsi", current_value=25, threshold=30,
            streak=3, horizon=3, rationale="first", path=path,
        )
        log_breaker_override(
            ticker="PANW", breaker_id="b", metric="rsi", current_value=25, threshold=30,
            streak=3, horizon=3, rationale="second", path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2


class TestCliLogOverride:
    def test_resolves_definition_and_state_then_logs(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        state_path = tmp_path / "thesis_breaker_state.json"
        overrides_path = tmp_path / "breaker-overrides.jsonl"
        target_path.write_text(_json.dumps({"holdings": [{
            "ticker": "NBIS", "thesisBreakers": [{
                "id": "nbis-trend-breakdown", "type": "auto", "metric": "trendState",
                "operator": "in", "threshold": ["DOWNTREND"], "horizon": 5,
                "note": "Sustained downtrend",
            }],
        }]}))
        state_path.write_text(_json.dumps({"holdings": {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 5, "status": "TRIGGERED",
        }}}}))

        _cli_log_override(
            ticker="NBIS", breaker_id="nbis-trend-breakdown",
            rationale="Vera Rubin ramp de-risks the downtrend",
            target_portfolio_path=target_path, state_path=state_path,
            overrides_path=overrides_path,
        )

        lines = overrides_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = _json.loads(lines[0])
        assert entry["metric"] == "trendState"
        assert entry["currentValue"] == "DOWNTREND"
        assert entry["streak"] == 5
        assert entry["horizon"] == 5
        assert entry["rationale"] == "Vera Rubin ramp de-risks the downtrend"

    def test_unknown_ticker_raises(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        target_path.write_text(_json.dumps({"holdings": []}))
        with pytest.raises(ValueError, match="not found in target-portfolio"):
            _cli_log_override(
                ticker="NOPE", breaker_id="x", rationale="r",
                target_portfolio_path=target_path, state_path=tmp_path / "s.json",
                overrides_path=tmp_path / "o.jsonl",
            )

    def test_unknown_breaker_id_raises(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        target_path.write_text(_json.dumps({"holdings": [{"ticker": "NBIS", "thesisBreakers": []}]}))
        with pytest.raises(ValueError, match="not found on NBIS"):
            _cli_log_override(
                ticker="NBIS", breaker_id="nope", rationale="r",
                target_portfolio_path=target_path, state_path=tmp_path / "s.json",
                overrides_path=tmp_path / "o.jsonl",
            )

    def test_missing_state_file_still_logs_with_null_streak(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        target_path.write_text(_json.dumps({"holdings": [{
            "ticker": "NBIS", "thesisBreakers": [{
                "id": "nbis-ndr-floor", "type": "manual", "metric": "ndr", "operator": "<",
                "threshold": 115, "horizon": "2 quarters", "note": "NDR floor",
                "status": "TRIGGERED", "statusSetAt": "2026-07-09",
                "statusSetBy": "agent", "reviewCadenceDays": 90,
            }],
        }]}))
        overrides_path = tmp_path / "breaker-overrides.jsonl"

        _cli_log_override(
            ticker="NBIS", breaker_id="nbis-ndr-floor", rationale="Board confirmed NDR recovery plan",
            target_portfolio_path=target_path, state_path=tmp_path / "does-not-exist.json",
            overrides_path=overrides_path,
        )

        entry = _json.loads(overrides_path.read_text().strip())
        assert entry["streak"] is None
        assert entry["horizon"] == "2 quarters"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_thesis_breakers.py -v`
Expected: FAIL with `ImportError: cannot import name 'compute_breaker_state'`

- [ ] **Step 3: Write minimal implementation**

Add to `investment_screener/backend/py_services/thesis_breakers.py` (after `evaluate_breakers`,
replacing the placeholder `main()`):

```python
def compute_breaker_state(
    conviction_scores: list[dict[str, Any]],
    market_regime: dict[str, Any] | None,
    pillar_health: list[dict[str, Any]],
    target_portfolio_path: Path = TARGET_PATH,
    state_path: Path = STATE_PATH,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load, evaluate, and persist thesis breaker state for this run.

    I/O wrapper around the pure evaluate_breakers(). Never mutates
    target_portfolio_path — only reads it. Owns state_path exclusively.

    Args:
        conviction_scores: This run's conviction score rows — pass the same
            list daily_brief.py already computed, never recompute here.
        market_regime: This run's market_regime output, or None.
        pillar_health: This run's pillar health list.
        target_portfolio_path: Path to target-portfolio.json.
        state_path: Path to thesis_breaker_state.json.

    Returns:
        (full_state_dict, triggered_list) — full_state_dict is the exact
        shape written to state_path; triggered_list is every breaker whose
        status is "TRIGGERED" this run, each entry merging its definition
        (metric/operator/threshold/horizon/note/type) with its evaluated
        state and the holding's targetWeight (for triage sort order).
    """
    with open(target_portfolio_path) as f:
        target_data = json.load(f)

    prev_state: dict[str, Any] = {}
    if state_path.exists():
        with open(state_path) as f:
            prev_state = json.load(f).get("holdings", {})

    today = date.today().isoformat()
    holdings_state = evaluate_breakers(
        target_data, conviction_scores, market_regime, pillar_health, prev_state, today
    )

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    full_state = {"generatedAt": now_iso, "holdings": holdings_state}

    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(full_state, f, indent=2)
    os.replace(tmp, state_path)

    breakers_by_id = {
        (h["ticker"], b["id"]): b
        for h in target_data.get("holdings", [])
        for b in h.get("thesisBreakers", [])
    }
    weight_by_ticker = {h["ticker"]: h.get("targetWeight") for h in target_data.get("holdings", [])}

    triggered: list[dict[str, Any]] = []
    for ticker, breakers in holdings_state.items():
        for breaker_id, entry in breakers.items():
            if entry.get("status") != "TRIGGERED":
                continue
            definition = breakers_by_id[(ticker, breaker_id)]
            triggered.append({
                "ticker": ticker,
                "breakerId": breaker_id,
                "targetWeight": weight_by_ticker.get(ticker),
                **definition,
                **entry,
            })

    return full_state, triggered


def log_breaker_override(
    ticker: str,
    breaker_id: str,
    metric: str,
    current_value: Any,
    threshold: Any,
    streak: int | None,
    horizon: Any,
    rationale: str,
    overridden_by: str = "user",
    path: Path = OVERRIDES_PATH,
) -> None:
    """Append one accountability-trail record for a TRIGGERED-breaker override.

    Called by the daily-loop-agent (not daily_brief.py itself) — only a human
    decision to hold through a TRIGGERED breaker constitutes an "override."

    Args:
        ticker: Holding ticker.
        breaker_id: The breaker's id, as defined in target-portfolio.json.
        metric: The breaker's metric name.
        current_value: The value that caused (or accompanies) the trigger.
        threshold: The breaker's threshold.
        streak: currentStreak at time of override (None for manual breakers).
        horizon: The breaker's horizon (int for auto, str for manual).
        rationale: The user's stated reason for holding through.
        overridden_by: Who made the call — defaults to "user".
        path: Target JSONL file.
    """
    entry = {
        "date": date.today().isoformat(),
        "ticker": ticker,
        "breakerId": breaker_id,
        "metric": metric,
        "currentValue": current_value,
        "threshold": threshold,
        "streak": streak,
        "horizon": horizon,
        "rationale": rationale,
        "overriddenBy": overridden_by,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _cli_log_override(
    ticker: str,
    breaker_id: str,
    rationale: str,
    overridden_by: str = "user",
    target_portfolio_path: Path = TARGET_PATH,
    state_path: Path = STATE_PATH,
    overrides_path: Path = OVERRIDES_PATH,
) -> None:
    """Resolve a breaker's definition + current state, then log an override.

    Thin wrapper so a caller (the daily-loop-agent, via `--log-override`) only
    needs a ticker, breaker id, and rationale — not thesis_breaker_state.json's
    internal shape.

    Args:
        ticker: Holding ticker.
        breaker_id: The breaker's id, as defined in target-portfolio.json.
        rationale: The user's stated reason for holding through.
        overridden_by: Who made the call — defaults to "user".
        target_portfolio_path: Path to target-portfolio.json.
        state_path: Path to thesis_breaker_state.json (missing file is fine —
            streak/currentValue are logged as None if state hasn't run yet).
        overrides_path: Target JSONL file.

    Raises:
        ValueError: If the ticker or breaker id isn't found.
    """
    with open(target_portfolio_path) as f:
        target_data = json.load(f)
    holding = next((h for h in target_data["holdings"] if h["ticker"] == ticker), None)
    if holding is None:
        raise ValueError(f"ticker '{ticker}' not found in target-portfolio.json")
    definition = next((b for b in holding.get("thesisBreakers", []) if b["id"] == breaker_id), None)
    if definition is None:
        raise ValueError(f"breaker id '{breaker_id}' not found on {ticker}")

    state: dict[str, Any] = {}
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f).get("holdings", {})
    entry = state.get(ticker, {}).get(breaker_id, {})

    log_breaker_override(
        ticker=ticker, breaker_id=breaker_id, metric=definition["metric"],
        current_value=entry.get("currentValue"), threshold=definition["threshold"],
        streak=entry.get("currentStreak"), horizon=definition["horizon"],
        rationale=rationale, overridden_by=overridden_by, path=overrides_path,
    )


def main() -> None:
    """CLI entry point — evaluate breakers standalone, or log an override.

    --log-override lets the daily-loop-agent record a TRIGGERED-breaker
    override without importing this module directly.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Thesis breaker evaluation / override logging")
    parser.add_argument("--log-override", action="store_true", help="Log an override instead of evaluating")
    parser.add_argument("--ticker", help="Ticker (required with --log-override)")
    parser.add_argument("--breaker-id", help="Breaker id (required with --log-override)")
    parser.add_argument("--rationale", help="Override rationale (required with --log-override)")
    parser.add_argument("--overridden-by", default="user", help="Who made the override call")
    args = parser.parse_args()

    if args.log_override:
        if not (args.ticker and args.breaker_id and args.rationale):
            sys.exit("ERROR: --log-override requires --ticker, --breaker-id, and --rationale")
        _cli_log_override(args.ticker, args.breaker_id, args.rationale, args.overridden_by)
        print(f"✅  Logged override for {args.ticker} / {args.breaker_id}")
        return

    from compute_conviction_scores import compute_all
    from dataclasses import asdict
    from market_regime import compute_market_regime

    scores_raw = [asdict(s) for s in compute_all()]
    try:
        market_regime = compute_market_regime()
    except Exception as exc:
        print(f"market_regime unavailable: {exc}", file=sys.stderr)
        market_regime = None

    with open(TARGET_PATH) as f:
        target_data = json.load(f)
    ticker_pillar = {h["ticker"]: h.get("subStrategyId", "unknown") for h in target_data["holdings"]}
    pillars: dict[str, list[int]] = {}
    for s in scores_raw:
        p = ticker_pillar.get(s["ticker"], "unknown")
        pillars.setdefault(p, []).append(s["total"])
    pillar_health = [
        {"pillar": p, "avg_score": round(sum(pts) / len(pts), 2), "count": len(pts),
         "min": min(pts), "max": max(pts)}
        for p, pts in pillars.items() if p not in ("unknown", "cash")
    ]

    _, triggered = compute_breaker_state(scores_raw, market_regime, pillar_health)
    if triggered:
        print(f"TRIGGERED breakers: {len(triggered)}")
        for t in triggered:
            print(f"  {t['ticker']}  {t['metric']} {t['operator']} {t['threshold']}")
    else:
        print("No TRIGGERED breakers.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_thesis_breakers.py -v`
Expected: PASS (40 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/thesis_breakers.py investment_screener/backend/tests/py_services/test_thesis_breakers.py
git commit -m "feat: add compute_breaker_state I/O wrapper and override logging (B5 task 3)"
```

---

## Task 4: `update_thesis.py` CLI — `--set-breaker` / `--set-breaker-status` / `--remove-breaker`

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/update_thesis.py`
- Test: `investment_screener/backend/tests/py_services/test_update_thesis_breakers.py` (new file
  — `update_thesis.py` has no existing test file to extend)

**Interfaces:**
- Produces (in `update_thesis.py`): `AUTO_METRICS`, `VALID_OPERATORS`, `VALID_STATUSES`
  (module constants, mirroring `thesis_breakers.py`'s — this file has no import path to
  `py_services/`, so the sets are duplicated here deliberately, same as `VALID_ROLES`
  already is), `validate_breaker(breaker: dict) -> list[str]`,
  `set_breaker(holding: dict, breaker: dict) -> None` (mutates `holding["thesisBreakers"]`,
  raises `ValueError` on duplicate id or validation failure),
  `set_breaker_status(holding: dict, breaker_id: str, status: str, note: str | None) -> None`
  (raises `ValueError` if breaker not found or not `type: "manual"`),
  `remove_breaker(holding: dict, breaker_id: str) -> None` (raises `ValueError` if not found)

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for update_thesis.py's thesisBreakers CLI functions (B5 task 4)."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
UPDATE_THESIS_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
sys.path.insert(0, str(UPDATE_THESIS_DIR))

from update_thesis import (  # noqa: E402
    AUTO_METRICS,
    remove_breaker,
    set_breaker,
    set_breaker_status,
    validate_breaker,
)


def _auto_breaker(**overrides) -> dict:
    b = {
        "id": "nbis-trend-breakdown",
        "type": "auto",
        "metric": "trendState",
        "operator": "in",
        "threshold": ["DOWNTREND"],
        "horizon": 5,
        "note": "Sustained downtrend",
    }
    b.update(overrides)
    return b


def _manual_breaker(**overrides) -> dict:
    b = {
        "id": "nbis-ndr-floor",
        "type": "manual",
        "metric": "ndr",
        "operator": "<",
        "threshold": 115,
        "horizon": "2 quarters",
        "note": "NDR floor",
        "status": "OK",
        "statusSetAt": "2026-07-01",
        "statusSetBy": "agent",
        "reviewCadenceDays": 90,
    }
    b.update(overrides)
    return b


class TestValidateBreaker:
    def test_valid_auto_breaker_has_no_errors(self):
        assert validate_breaker(_auto_breaker()) == []

    def test_valid_manual_breaker_has_no_errors(self):
        assert validate_breaker(_manual_breaker()) == []

    def test_missing_id_is_an_error(self):
        b = _auto_breaker()
        del b["id"]
        errors = validate_breaker(b)
        assert any("id" in e for e in errors)

    def test_invalid_type_is_an_error(self):
        errors = validate_breaker(_auto_breaker(type="weird"))
        assert any("type" in e for e in errors)

    def test_auto_metric_outside_enum_is_an_error(self):
        errors = validate_breaker(_auto_breaker(metric="madeUpMetric"))
        assert any("metric" in e for e in errors)

    def test_manual_metric_is_unrestricted(self):
        assert validate_breaker(_manual_breaker(metric="anything")) == []

    def test_invalid_operator_is_an_error(self):
        errors = validate_breaker(_auto_breaker(operator="!="))
        assert any("operator" in e for e in errors)

    def test_in_operator_requires_list_threshold(self):
        errors = validate_breaker(_auto_breaker(operator="in", threshold="DOWNTREND"))
        assert any("threshold" in e for e in errors)

    def test_manual_breaker_missing_status_is_an_error(self):
        b = _manual_breaker()
        del b["status"]
        errors = validate_breaker(b)
        assert any("status" in e for e in errors)

    def test_manual_breaker_invalid_status_is_an_error(self):
        errors = validate_breaker(_manual_breaker(status="MAYBE"))
        assert any("status" in e for e in errors)


class TestSetBreaker:
    def test_adds_breaker_to_holding_with_none_yet(self):
        holding = {"ticker": "NBIS"}
        set_breaker(holding, _auto_breaker())
        assert holding["thesisBreakers"] == [_auto_breaker()]

    def test_appends_to_existing_breakers(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_manual_breaker()]}
        set_breaker(holding, _auto_breaker())
        assert len(holding["thesisBreakers"]) == 2

    def test_duplicate_id_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker()]}
        with pytest.raises(ValueError, match="already exists"):
            set_breaker(holding, _auto_breaker())

    def test_invalid_breaker_raises(self):
        holding = {"ticker": "NBIS"}
        with pytest.raises(ValueError, match="Invalid breaker"):
            set_breaker(holding, _auto_breaker(operator="!="))


class TestSetBreakerStatus:
    def test_updates_manual_breaker_status(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_manual_breaker()]}
        set_breaker_status(holding, "nbis-ndr-floor", "TRIGGERED", "Q2 NDR 108%")
        b = holding["thesisBreakers"][0]
        assert b["status"] == "TRIGGERED"
        assert b["statusSetAt"] == __import__("datetime").date.today().isoformat()

    def test_missing_breaker_id_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_manual_breaker()]}
        with pytest.raises(ValueError, match="not found"):
            set_breaker_status(holding, "does-not-exist", "TRIGGERED", None)

    def test_auto_breaker_status_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker()]}
        with pytest.raises(ValueError, match="manual"):
            set_breaker_status(holding, "nbis-trend-breakdown", "TRIGGERED", None)


class TestRemoveBreaker:
    def test_removes_matching_breaker(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker(), _manual_breaker()]}
        remove_breaker(holding, "nbis-trend-breakdown")
        assert len(holding["thesisBreakers"]) == 1
        assert holding["thesisBreakers"][0]["id"] == "nbis-ndr-floor"

    def test_missing_id_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker()]}
        with pytest.raises(ValueError, match="not found"):
            remove_breaker(holding, "does-not-exist")


def test_auto_metrics_matches_thesis_breakers_module():
    assert AUTO_METRICS == frozenset({
        "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
    })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_update_thesis_breakers.py -v`
Expected: FAIL with `ImportError: cannot import name 'validate_breaker'`

- [ ] **Step 3: Write minimal implementation**

In `plugins/portfolio-advisor/scripts/update_thesis.py`, add after `VALID_ROLES = {...}` (around
line 57):

```python
AUTO_METRICS = frozenset({
    "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
})
VALID_OPERATORS = frozenset({"<", "<=", ">", ">=", "==", "in"})
VALID_STATUSES = frozenset({"OK", "WATCHING", "TRIGGERED"})
```

Add after `apply_patch()` (around line 192, before the `# ── CLI ──` comment):

```python
def validate_breaker(breaker: dict) -> list[str]:
    """Validate a thesisBreakers entry before it's written to target-portfolio.json.

    Args:
        breaker: A single breaker dict (auto or manual — see spec §2.1).

    Returns:
        List of human-readable error strings; empty if valid.
    """
    errors: list[str] = []
    if not breaker.get("id"):
        errors.append("breaker missing 'id'")
    if breaker.get("type") not in ("auto", "manual"):
        errors.append(f"breaker 'type' must be 'auto' or 'manual', got {breaker.get('type')!r}")
    if breaker.get("type") == "auto" and breaker.get("metric") not in AUTO_METRICS:
        errors.append(f"auto breaker 'metric' must be one of {sorted(AUTO_METRICS)}, got {breaker.get('metric')!r}")
    if breaker.get("operator") not in VALID_OPERATORS:
        errors.append(f"'operator' must be one of {sorted(VALID_OPERATORS)}, got {breaker.get('operator')!r}")
    if breaker.get("operator") == "in" and not isinstance(breaker.get("threshold"), list):
        errors.append("operator 'in' requires 'threshold' to be a list")
    if breaker.get("type") == "manual":
        if breaker.get("status") not in VALID_STATUSES:
            errors.append(f"manual breaker 'status' must be one of {sorted(VALID_STATUSES)}, got {breaker.get('status')!r}")
        if not breaker.get("statusSetAt"):
            errors.append("manual breaker missing 'statusSetAt'")
        if not breaker.get("reviewCadenceDays"):
            errors.append("manual breaker missing 'reviewCadenceDays'")
    return errors


def set_breaker(holding: dict, breaker: dict) -> None:
    """Add a new breaker to a holding's thesisBreakers list.

    Args:
        holding: The holding dict from target-portfolio.json (mutated in place).
        breaker: The breaker to add — validated before insertion.

    Raises:
        ValueError: If the breaker fails validate_breaker(), or its id
            already exists on this holding.
    """
    errors = validate_breaker(breaker)
    if errors:
        raise ValueError(f"Invalid breaker: {'; '.join(errors)}")
    existing = holding.setdefault("thesisBreakers", [])
    if any(b["id"] == breaker["id"] for b in existing):
        raise ValueError(f"breaker id '{breaker['id']}' already exists on {holding.get('ticker')}")
    existing.append(breaker)


def set_breaker_status(holding: dict, breaker_id: str, status: str, note: str | None) -> None:
    """Update a manual breaker's status.

    Args:
        holding: The holding dict (mutated in place).
        breaker_id: id of the breaker to update.
        status: New status — must be one of VALID_STATUSES.
        note: Optional note appended to the breaker's 'note' field.

    Raises:
        ValueError: If the breaker isn't found, or isn't type "manual".
    """
    breaker = next((b for b in holding.get("thesisBreakers", []) if b["id"] == breaker_id), None)
    if breaker is None:
        raise ValueError(f"breaker id '{breaker_id}' not found on {holding.get('ticker')}")
    if breaker["type"] != "manual":
        raise ValueError(f"breaker '{breaker_id}' is type '{breaker['type']}' — status can only be set on manual breakers")
    breaker["status"] = status
    breaker["statusSetAt"] = datetime.now(timezone.utc).date().isoformat()
    if note:
        breaker["note"] = note


def remove_breaker(holding: dict, breaker_id: str) -> None:
    """Remove a breaker from a holding's thesisBreakers list.

    Args:
        holding: The holding dict (mutated in place).
        breaker_id: id of the breaker to remove.

    Raises:
        ValueError: If no breaker with that id exists on this holding.
    """
    existing = holding.get("thesisBreakers", [])
    remaining = [b for b in existing if b["id"] != breaker_id]
    if len(remaining) == len(existing):
        raise ValueError(f"breaker id '{breaker_id}' not found on {holding.get('ticker')}")
    holding["thesisBreakers"] = remaining
```

Wire into the CLI. In the `argparse` setup (around line 222-230), add:

```python
    parser.add_argument("--set-breaker", help="JSON breaker object to add to --holding's thesisBreakers")
    parser.add_argument("--set-breaker-status", metavar="BREAKER_ID", help="Breaker id whose status to update (manual breakers only)")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), help="New status for --set-breaker-status")
    parser.add_argument("--remove-breaker", metavar="BREAKER_ID", help="Breaker id to remove from --holding's thesisBreakers")
```

In `main()`, inside the existing `if args.holding:` block (around line 269-279), add after the
existing `if args.thesis:` handling:

```python
        if args.set_breaker:
            breaker = json.loads(args.set_breaker)
            set_breaker(holding, breaker)
        if args.set_breaker_status:
            if not args.status:
                sys.exit("ERROR: --set-breaker-status requires --status")
            set_breaker_status(holding, args.set_breaker_status, args.status, args.note)
        if args.remove_breaker:
            remove_breaker(holding, args.remove_breaker)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_update_thesis_breakers.py -v`
Expected: PASS (19 tests)

- [ ] **Step 5: Manual smoke test against the real CLI (dry-run, no write)**

Run:
```bash
python3 plugins/portfolio-advisor/scripts/update_thesis.py --holding NBIS \
  --set-breaker '{"id":"nbis-smoke-test","type":"auto","metric":"rsi","operator":"<","threshold":25,"horizon":3,"note":"smoke test"}' \
  --dry-run
```
Expected: prints the dry-run diff showing `NBIS` with the new breaker, exits 0, and — because
`--dry-run` is set — `target-portfolio.json` is unchanged (`git status --short` shows no diff
on that file).

Then confirm `--set-breaker-status` and `--remove-breaker` are wired the same way (still
`--dry-run`, still no write):
```bash
python3 plugins/portfolio-advisor/scripts/update_thesis.py --holding NBIS \
  --set-breaker '{"id":"nbis-smoke-test-2","type":"manual","metric":"ndr","operator":"<","threshold":115,"horizon":"2 quarters","note":"smoke test","status":"OK","statusSetAt":"2026-07-09","statusSetBy":"agent","reviewCadenceDays":90}' \
  --dry-run
python3 plugins/portfolio-advisor/scripts/update_thesis.py --holding NBIS \
  --set-breaker-status nbis-smoke-test-2 --status TRIGGERED --note "smoke test status change" --dry-run
python3 plugins/portfolio-advisor/scripts/update_thesis.py --holding NBIS \
  --remove-breaker nbis-smoke-test-2 --dry-run
```
Expected: all three print a dry-run diff and exit 0; `git status --short` still shows no diff
on `target-portfolio.json` after all three.

- [ ] **Step 6: Commit**

```bash
git add plugins/portfolio-advisor/scripts/update_thesis.py investment_screener/backend/tests/py_services/test_update_thesis_breakers.py
git commit -m "feat: add --set-breaker/--set-breaker-status/--remove-breaker to update_thesis.py (B5 task 4)"
```

---

## Task 5: `daily_brief.py` integration — evaluation + top-of-triage rendering

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py` (canonical — `investment_screener/backend/py_services/daily_brief.py` is a symlink to this file; editing either resolves to the same content, but always reference the canonical path)
- Test: `investment_screener/backend/tests/py_services/test_daily_brief_thesis_breakers.py` (new
  file — no `test_daily_brief.py` exists yet, so this stays scoped to just the new behavior)

**Interfaces:**
- Consumes: `thesis_breakers.compute_breaker_state` (Task 3)
- Produces: `render(brief)` output containing a `THESIS BREAKER TRIGGERED` block as the first
  content section (before `OVERNIGHT GAPS`, before any `REDUCE / EXIT` or `ACCUMULATE`
  section) whenever `brief["thesis_breakers_triggered"]` is non-empty; a `MANUAL BREAKERS
  NEEDING REVIEW` note near pillar health whenever any manual breaker is stale.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for daily_brief.py's B5 thesis-breaker triage integration."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from daily_brief import render  # noqa: E402


def _minimal_brief(**overrides) -> dict:
    brief = {
        "overnight_gaps": [],
        "date": "2026-07-09",
        "timestamp": "2026-07-09T13:00:00Z",
        "macro_regime": {"regime": "NEUTRAL", "score": 0, "degraded": False},
        "market_regime": None,
        "risk_snapshot": None,
        "ta_refreshed": False,
        "ta_skip_reason": "",
        "conviction_scores": [],
        "recommendations": [],
        "total_equity": 10000.0,
        "score_deltas": {},
        "pillar_health": [],
        "pillar_deltas": {},
        "earnings_flags": [],
        "yesterday_date": "2026-07-08",
        "thesis_breakers": None,
        "thesis_breakers_triggered": [],
    }
    brief.update(overrides)
    return brief


class TestRenderNoBreakersTriggered:
    def test_no_triggered_block_when_list_empty(self):
        output = render(_minimal_brief())
        assert "THESIS BREAKER TRIGGERED" not in output


class TestRenderTriggeredBreakerAtTopOfTriage:
    def _triggered_brief(self):
        return _minimal_brief(
            overnight_gaps=[{"ticker": "AAPL", "direction": "UP", "change_pct": 3.0,
                              "current": 200.0, "prev_close": 194.0, "market_state": "PRE"}],
            conviction_scores=[{
                "ticker": "NBIS", "total": -3, "band": "EXIT", "dcf_pts": -2, "ta_pts": -1,
                "weight_gap_pts": 0, "momentum_pts": 0, "dcf_action": "SELL",
                "pct_to_fv": -40.0, "rsi": 22.0, "adx": 30.0, "vol_bias": 1.0,
                "actual_weight": 3.7, "target_weight": 5.5, "weight_gap": 1.8,
                "flags": [], "ta_staleness_days": 0,
            }],
            thesis_breakers_triggered=[{
                "ticker": "NBIS", "breakerId": "nbis-trend-breakdown", "targetWeight": 5.5,
                "type": "auto", "metric": "trendState", "operator": "in",
                "threshold": ["DOWNTREND"], "horizon": 5,
                "note": "Sustained downtrend contradicts the thesis",
                "currentValue": "DOWNTREND", "conditionMet": True, "currentStreak": 5,
                "streakStartDate": "2026-07-05", "lastEvaluatedAt": "2026-07-09T13:00:00Z",
                "status": "TRIGGERED",
            }],
        )

    def test_triggered_block_appears_before_overnight_gaps(self):
        output = render(self._triggered_brief())
        assert "THESIS BREAKER TRIGGERED" in output
        assert output.index("THESIS BREAKER TRIGGERED") < output.index("OVERNIGHT GAPS")

    def test_triggered_block_appears_before_reduce_exit_section(self):
        output = render(self._triggered_brief())
        assert output.index("THESIS BREAKER TRIGGERED") < output.index("REDUCE / EXIT")

    def test_triggered_block_shows_ticker_metric_and_streak(self):
        output = render(self._triggered_brief())
        assert "NBIS" in output
        assert "trendState" in output
        assert "5/5" in output
        assert "Sustained downtrend contradicts the thesis" in output

    def test_multiple_triggered_sorted_by_target_weight_descending(self):
        brief = self._triggered_brief()
        brief["thesis_breakers_triggered"].append({
            "ticker": "PANW", "breakerId": "panw-rsi-floor", "targetWeight": 5.9,
            "type": "auto", "metric": "rsi", "operator": "<", "threshold": 25, "horizon": 3,
            "note": "RSI breakdown", "currentValue": 20.0, "conditionMet": True,
            "currentStreak": 3, "streakStartDate": "2026-07-07",
            "lastEvaluatedAt": "2026-07-09T13:00:00Z", "status": "TRIGGERED",
        })
        output = render(brief)
        assert output.index("PANW") < output.index("NBIS")


class TestRenderManualBreakerStaleness:
    def test_stale_manual_breaker_renders_review_note(self):
        brief = _minimal_brief(thesis_breakers={
            "generatedAt": "2026-07-09T13:00:00Z",
            "holdings": {"NBIS": {"nbis-ndr-floor": {
                "type": "manual", "status": "OK", "statusSetAt": "2026-04-01",
                "reviewCadenceDays": 90, "daysSinceReview": 99, "stale": True,
            }}},
        })
        output = render(brief)
        assert "MANUAL BREAKERS NEEDING REVIEW" in output
        assert "NBIS" in output
        assert "nbis-ndr-floor" in output

    def test_non_stale_manual_breaker_no_review_note(self):
        brief = _minimal_brief(thesis_breakers={
            "generatedAt": "2026-07-09T13:00:00Z",
            "holdings": {"NBIS": {"nbis-ndr-floor": {
                "type": "manual", "status": "OK", "statusSetAt": "2026-07-01",
                "reviewCadenceDays": 90, "daysSinceReview": 8, "stale": False,
            }}},
        })
        output = render(brief)
        assert "MANUAL BREAKERS NEEDING REVIEW" not in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_daily_brief_thesis_breakers.py -v`
Expected: FAIL — `THESIS BREAKER TRIGGERED` assertions fail (block doesn't exist yet)

- [ ] **Step 3: Write minimal implementation**

In `plugins/portfolio-advisor/scripts/daily_brief.py`, add the import inside `run()` alongside
the other `py_services` imports (near line 175):

```python
    from thesis_breakers import compute_breaker_state
```

Add a new pipeline step in `run()` right after pillar health is computed (after
`pillars = _pillar_summary(scores_raw, target_data)`, around line 264):

```python
    # ── 5b. Thesis breaker evaluation (B5 — additive, top-of-triage) ──────────
    print("▶ Thesis breakers...", file=sys.stderr)
    try:
        breaker_state, triggered_breakers = compute_breaker_state(
            conviction_scores=scores_raw,
            market_regime=market_regime,
            pillar_health=pillars,
        )
    except Exception as exc:
        print(f"  Thesis breakers skipped: {exc}", file=sys.stderr)
        breaker_state, triggered_breakers = None, []
```

Add the two new keys to the `brief` dict literal (around line 287-304):

```python
        "thesis_breakers": breaker_state,
        "thesis_breakers_triggered": triggered_breakers,
```

In `render()`, insert the triggered-breaker block as the very first content, right after the
header lines and before the `overnight gaps` section (around line 337-338):

```python
    # ── Thesis breakers (B5 — top of triage, above all TA signals) ────────────
    triggered = brief.get("thesis_breakers_triggered") or []
    if triggered:
        triggered_sorted = sorted(triggered, key=lambda b: -(b.get("targetWeight") or 0))
        lines.append(f"\n🚨  THESIS BREAKER TRIGGERED — {len(triggered_sorted)} holding(s):")
        for b in triggered_sorted:
            thr = b["threshold"]
            thr_str = ",".join(str(t) for t in thr) if isinstance(thr, list) else str(thr)
            if b["type"] == "auto":
                detail = f"(current: {b.get('currentValue')}, {b.get('currentStreak')}/{b.get('horizon')} consecutive runs)"
            else:
                detail = f"(manually flagged TRIGGERED on {b.get('statusSetAt')})"
            lines.append(f"    {b['ticker']:<8} {b['metric']} {b['operator']} {thr_str}  {detail}")
            if b.get("note"):
                lines.append(f"          \"{b['note']}\"")
```

Add the stale-manual-breaker note after the pillar health block, before the footer (around
line 469-470, right after the pillar health `for p in pillars:` loop):

```python
    # ── Manual breaker staleness (B5) ──────────────────────────────────────────
    stale_manual: list[tuple[str, str, dict[str, Any]]] = []
    if brief.get("thesis_breakers"):
        for ticker, breakers in brief["thesis_breakers"].get("holdings", {}).items():
            for bid, entry in breakers.items():
                if entry.get("type") == "manual" and entry.get("stale"):
                    stale_manual.append((ticker, bid, entry))
    if stale_manual:
        lines.append(f"\n🕰   MANUAL BREAKERS NEEDING REVIEW — {len(stale_manual)}:")
        for ticker, bid, entry in stale_manual:
            lines.append(
                f"    {ticker:<8} {bid}  last set {entry.get('statusSetAt')} "
                f"({entry.get('daysSinceReview')}d ago, cadence {entry.get('reviewCadenceDays')}d)"
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_daily_brief_thesis_breakers.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Run the full existing test suite to confirm no regressions**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/ -v`
Expected: PASS — all prior tests (market_regime, risk_engine, thesis_breakers,
update_thesis_breakers, daily_brief_thesis_breakers) plus this task's new tests, zero failures.

- [ ] **Step 6: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py investment_screener/backend/tests/py_services/test_daily_brief_thesis_breakers.py
git commit -m "feat: wire thesis breaker evaluation into daily_brief.py triage (B5 task 5)"
```

---

## Task 6: `set-thesis-breakers` skill — interactive HITL authoring

**Files:**
- Create: `plugins/portfolio-advisor/skills/set-thesis-breakers/SKILL.md`
- Create: `plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json`
- Modify: `plugins/portfolio-advisor/plugin.json`
- Modify: `plugins/portfolio-advisor/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: `update_thesis.py --set-breaker` / `--set-breaker-status` / `--remove-breaker`
  (Task 4) as its sole write path — this skill contains no new Python script.

This task has no pytest suite — it's a conversational skill (prose + one CLI dry run for
verification), matching the `norberts-gambit` skill's shape (`SKILL.md` + no `scripts/` dir,
since it invokes the existing canonical `update_thesis.py` directly rather than owning new
code). `evals/evals.json` is created empty, matching the repo-wide convention (G3 in the
elevation guide — filling skill evals is explicit Phase 6 scope, not B5's).

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: set_thesis_breakers
plugin: portfolio-advisor
description: >
  Interactive, HITL-first session to define a holding's thesis breakers — the
  specific, measurable conditions that would mean the investment thesis is
  broken. Reads the holding's existing rationale, DCF params, and framework
  score to propose 2-3 candidate breakers instead of a blank-page ask,
  classifies each as auto-evaluated (checked daily) or manual (agent/user
  reviews periodically) in plain language, and confirms every breaker in
  plain English before writing anything — the user never sees or writes raw
  JSON. Trigger: "/set-thesis-breakers {TICKER}", "set breakers for {TICKER}",
  "what would break this thesis", or as the suggested next step right after
  /evaluate-stock produces a fresh thesis.
allowed-tools: Bash, Read, Ask
---

# Set Thesis Breakers Skill

## Purpose
The investment framework requires "3 specific, measurable thesis breakers" per holding —
concrete conditions that, if met, mean the original investment case no longer holds. This
skill is how a user actually authors them: interactively, with the skill doing the reading
and the drafting, and the user doing the deciding.

This is deliberately **not** a new agent — it's a focused conversational skill, the same
shape as `calibrate-targets`, that ends by calling `update_thesis.py` under the hood.

---

## HITL is the point of this skill, not an afterthought

Every breaker gets written only after the user has seen it explained in plain language and
explicitly confirmed it — never a silent default, never inferred and saved without a turn
where the user can reject or rewrite it. This mirrors the repo's standing constraint that
human-in-the-loop is sacred for trade execution — applied here to thesis authorship instead.

---

## Persona
You are a **thorough but efficient thesis interviewer** — not a form-filler. You've already
read the holding's rationale and data before asking anything, so your first message to the
user should already contain a real proposal, not a blank "what are your breakers?" question.
You explain tradeoffs (auto vs. manual, streak horizons, review cadence) in plain language
every time — never assume the user remembers the schema from a prior session.

---

## Flow

### Step 1 — Read before asking anything
For the target ticker, read:
- `investment_screener/backend/data/theses/target-portfolio.json` → the holding's
  `thesisForInclusion` and any existing `thesisBreakers`.
- `investment_screener/backend/data/projections/{TICKER}.json` → `aiThesis.rationale`,
  `aiThesis.fairValue`, `analyticsLog.framework` / `analyticsLog.peerBench` /
  `analyticsLog.technicals` (Phase 2b, if present — a holding valued before Phase 2b may not
  have these; proceed without them if absent, don't block on missing data), scenario
  `growthRate`/`netMargin` assumptions.

### Step 2 — Propose 2-3 candidates from what's already there
Do not start from a blank page. Scan the rationale for anything resembling a measurable
claim — a margin target, a growth-rate assumption, a named risk, a competitive moat claim —
and turn 2-3 of them into concrete `metric`/`operator`/`threshold` candidates. If the
rationale is too thin to derive anything, say so honestly and ask the user what would change
their mind on this position.

### Step 3 — One candidate at a time: keep / edit / reject / write your own
For each candidate, ask (one question, multiple choice):
- Keep as proposed
- Edit the threshold or condition
- Reject it
- Write a different one from scratch

### Step 4 — Classify auto vs. manual, explained plainly
The five metrics `daily_brief.py` can check automatically every run: RSI, the DCF
fair-value gap, C2's trend state (uptrend/downtrend/weakening/basing), momentum percentile,
and pillar average score. Anything else — NDR, gross retention, backlog growth, a
qualitative competitive claim — must be `manual`. When a candidate needs `manual`, say so
explicitly:

> "This one needs you to check in — I can't watch NDR automatically, so I'll flag it for
> review every N days instead of catching it live."

### Step 5 — For auto breakers: state the horizon honestly
> "This needs 5 consecutive daily runs to confirm — it won't fire on a single bad day."

Ask the user if the default horizon (5 for RSI/trend-style breakers, 3 for faster-moving
ones) feels right, or if they want it tighter/looser.

### Step 6 — For manual breakers: capture the review cadence
> "I'll remind you to revisit this every ~45 days — right, or does this need checking more
> or less often?"

Default to 45 days if the user has no preference; use 90 for anything tied to quarterly
disclosures (NDR, GRR, backlog) since that's the natural reporting cadence.

### Step 7 — Soft-nudge toward 3, never hard-block
If the session ends with fewer than 2 breakers set, say so and ask if that's intentional —
some theses genuinely have only 1-2 clean, measurable breakers. Never refuse to finish the
session over the count.

### Step 8 — Confirm in plain English, then write
Before calling `update_thesis.py`, summarize every breaker about to be written in one
sentence each and get an explicit "yes, save these." Then, for each breaker:

```bash
python3 plugins/portfolio-advisor/scripts/update_thesis.py --holding {TICKER} \
  --set-breaker '{"id":"...","type":"auto","metric":"...","operator":"...","threshold":...,"horizon":...,"note":"..."}' \
  --note "set via /set-thesis-breakers"
```

For manual breakers, the JSON also includes `"status":"OK"`, today's date as
`"statusSetAt"`, `"statusSetBy":"agent"`, and the agreed `"reviewCadenceDays"`.

The user never sees or writes this JSON themselves — it's assembled from what they already
confirmed in plain English in Step 3/5/6.

---

## Editing an existing breaker
Same conversational loop as authoring a new one (Steps 3/5/6), whether the breaker hasn't
been written yet or already exists. For an already-committed breaker, this skill calls
`--remove-breaker` immediately followed by `--set-breaker` with the updated definition — two
CLI calls, invisible to the user as anything other than "updating this one breaker." There
is no separate `--edit-breaker` flag by design (see
`docs/superpowers/specs/2026-07-09-thesis-breakers-design.md` §6).

---

## What this skill does NOT do
- Does not evaluate breakers — that's `daily_brief.py` + `thesis_breakers.py`, every
  `/daily` run.
- Does not decide overrides when a breaker later triggers — that's the daily-loop-agent's
  job during triage, logged via `thesis_breakers.log_breaker_override()`.
- Does not hand-block on hitting exactly 3 breakers (Step 7).
```

- [ ] **Step 2: Create the empty evals scaffold**

```json
{"evals": []}
```

Write this to `plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json` —
matches the existing empty-scaffold convention across the repo's other skills (filling it in
is Phase 6 / G3 scope, not B5's).

- [ ] **Step 3: Register the skill in `plugins/portfolio-advisor/plugin.json`**

Read the current `"version"` field first (`grep -n '"version"' plugins/portfolio-advisor/plugin.json`)
and bump the patch-minor segment by one (e.g. `2.1.0` → `2.2.0` if that's what's currently
there — match whatever the real current value is, don't assume it's still `2.1.0` by the time
this task runs). Update the top-level `"description"` to append
`/set-thesis-breakers (interactive HITL thesis-breaker authoring)` to the skill list, and add
a new entry to the `"skills"` array (alphabetically near `calibrate_targets`):

```json
        {
            "name": "set_thesis_breakers",
            "path": "skills/set-thesis-breakers/SKILL.md",
            "trigger": "/set-thesis-breakers"
        },
```

- [ ] **Step 4: Register in `plugins/portfolio-advisor/.claude-plugin/plugin.json`**

Same version bump (must match Step 3's new version exactly), and append
`/set-thesis-breakers (interactive HITL thesis-breaker authoring)` to this file's
`"description"` string too (this manifest has no `"skills"` array — description-only, same
pattern the `norberts-gambit` skill followed).

- [ ] **Step 5: Register in `.claude-plugin/marketplace.json`**

Find the `"name": "portfolio-advisor"` entry and append
`/set-thesis-breakers (interactive HITL thesis-breaker authoring)` to its `"description"`
string, in the same list-of-skills style as the existing entries.

- [ ] **Step 6: Verify JSON validity and registration**

Run:
```bash
python3 -c "import json; json.load(open('plugins/portfolio-advisor/plugin.json'))" && echo OK
python3 -c "import json; json.load(open('plugins/portfolio-advisor/.claude-plugin/plugin.json'))" && echo OK
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))" && echo OK
python3 -c "
import json
d = json.load(open('plugins/portfolio-advisor/plugin.json'))
assert any(s['trigger'] == '/set-thesis-breakers' for s in d['skills']), 'not registered'
print('registered OK')
"
```
Expected: `OK` three times, then `registered OK`.

- [ ] **Step 7: Commit**

```bash
git add plugins/portfolio-advisor/skills/set-thesis-breakers/ plugins/portfolio-advisor/plugin.json plugins/portfolio-advisor/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "feat: add set-thesis-breakers interactive HITL authoring skill (B5 task 6)"
```

---

## Task 7: Wire TRIGGERED-breaker escalation + override logging into `daily-loop-agent.md`

**Files:**
- Modify: `plugins/portfolio-advisor/agents/daily-loop-agent.md`

**Interfaces:**
- Consumes: `brief["thesis_breakers_triggered"]` (Task 5's addition to the JSON `daily_brief.py
  --json` already emits), `thesis_breakers.py --log-override` CLI (Task 3)

No pytest suite — this is agent-instruction prose, verified by a manual walkthrough (Step 3
below), same as Task 6.

- [ ] **Step 1: Add `[THESIS BREAKER]` as the top priority-queue item type**

In `plugins/portfolio-advisor/agents/daily-loop-agent.md`, Step 2's priority queue example
(around line 156-174), add a new item 1 above the existing `[IMMINENT EVENT]` item and
renumber the rest:

```
Here's what I'm seeing today, ranked by urgency:

1. [THESIS BREAKER] TICKER — {metric} {operator} {threshold} TRIGGERED ({streak}/{horizon} runs)
   "{note}" — this is a pre-declared condition for selling. Hold anyway, or act on it?

2. [IMMINENT EVENT] TICKER — earns in N days, currently [REDUCE/EXIT], pre-event size check needed
   P&L: [+/-X%] · Score: [X] · Reason: [1-line why this needs attention before earnings]

3. [EXIT] TICKER — score [X], [Nth] consecutive day at EXIT
   P&L: [+/-X%] · Reason: [DCF action + TA signal, e.g. "DCF SELL, RSI 78 cooling, thesis broken"]

4. [EXIT] TICKER — score [X], new signal
   P&L: [+/-X%] · Reason: [what flipped today]

5. [REDUCE] TICKER — score [X], overweight [+X.X%]
   P&L: [+/-X%] · Reason: [why reduce, e.g. "RSI OB, at resistance, +18% above book"]

6. [ACCUMULATE] TICKER — score [+X], [X]% to fair value, [X.X]% underweight
   P&L: [+/-X%] · Reason: [why now, e.g. "DCF BUY, RSI oversold, at support"]

Start with item 1, or jump to a specific one?
```

Update the **Priority rules** list (around line 177-185) to add a new rule 0, renumbering the
rest:

```
**Priority rules:**
0. TRIGGERED thesis breakers — always first, above imminent earnings. A breaker only
   exists because the user or agent pre-declared it as a reason to sell; surfacing it late
   defeats the point.
1. IMMINENT earnings on any REDUCE/EXIT position (size before event)
2. EXIT signals that have been EXIT for 2+ consecutive sessions
3. EXIT signals (new)
4. REDUCE signals that are > 2% overweight their target
5. REDUCE signals
6. APPROACHING earnings on ACCUMULATE positions (buy before, or wait?)
7. ACCUMULATE signals (only present if macro is RISK-ON or NEUTRAL ≥ +4)
8. Stale DCF tickers (no projection file in 30+ days) — offer to refresh
```

- [ ] **Step 2: Add a THESIS BREAKER card format + the override-logging instruction**

In Step 3 ("Interactive Action Cards"), add a new card format immediately before the
existing **Card format** block (around line 197):

````
**THESIS BREAKER card format (present these before any other card type):**
```
─── [N]/[TOTAL] · THESIS BREAKER: [TICKER] ───────────────────
  [Company Name]  ·  Breaker: [breaker id]

  Condition:  [metric] [operator] [threshold]
  Streak:     [currentStreak]/[horizon] consecutive daily runs   (auto breakers)
              -- OR --
  Manually flagged TRIGGERED on [statusSetAt]                    (manual breakers)
  Note:       "[note]"

  This is a pre-declared condition the user set as a reason to sell this
  position. It does not auto-execute anything — you decide.

→ Act on it (sell/trim), or hold anyway with a stated reason?
──────────────────────────────────────────────────────────────
```

**If the user chooses "hold anyway"** — this is an override, and the framework requires an
accountability trail. Ask for a one-sentence rationale, then log it before moving to the
next card:

```bash
python3 investment_screener/backend/py_services/thesis_breakers.py --log-override \
  --ticker {TICKER} --breaker-id {breaker_id} --rationale "{user's stated reason}"
```

**If the user chooses to act on it** (sell/trim) — proceed exactly like an EXIT/REDUCE card:
build the trade proposal, confirm, execute. No override log is written, since the breaker's
own recommendation was followed, not overridden.

A TRIGGERED breaker never auto-executes a trade on its own — same HITL rule as every other
signal in this loop.
````

- [ ] **Step 3: Manual walkthrough verification**

Since this task has no pytest suite, verify the three edits landed correctly:

```bash
grep -n "THESIS BREAKER" plugins/portfolio-advisor/agents/daily-loop-agent.md
grep -n "log-override" plugins/portfolio-advisor/agents/daily-loop-agent.md
```
Expected: the first `grep` finds at least 3 matches (priority-queue item, priority rule 0,
card format section); the second finds the `--log-override` CLI invocation instruction. This
is a documentation-wiring check, not a runtime test — Task 5's
`test_daily_brief_thesis_breakers.py` already proves the underlying data and rendering are
correct; this task only proves the agent's instructions actually reference them.

- [ ] **Step 4: Commit**

```bash
git add plugins/portfolio-advisor/agents/daily-loop-agent.md
git commit -m "docs: wire thesis-breaker triage priority and override logging into daily-loop-agent (B5 task 7)"
```

---

## Final step: whole-branch review

After all 7 tasks are committed in the worktree, follow the same pattern as E1/C2: request a
final whole-branch review (opus) before merging to local `main`. Specifically check:
- `data/thesis_breaker_state.json` is never written by anything other than
  `thesis_breakers.compute_breaker_state()`.
- `target-portfolio.json` is never mutated by `thesis_breakers.py` — only by
  `update_thesis.py`'s `save_thesis()` path.
- `data/theses/breaker-overrides.jsonl` is only ever appended to (via `log_breaker_override`/
  `_cli_log_override`), never rewritten or truncated.
- The Phase 3 acceptance criterion literally holds: run
  `python3 -m pytest investment_screener/backend/tests/py_services/test_daily_brief_thesis_breakers.py -v`
  and confirm `test_triggered_block_appears_before_overnight_gaps` and
  `test_triggered_block_appears_before_reduce_exit_section` both pass — this is the fixture
  proof that "a fixture triggered thesis-breaker appears at top of triage."
- Run the full new test surface together:
  `python3 -m pytest investment_screener/backend/tests/py_services/test_thesis_breakers.py investment_screener/backend/tests/py_services/test_update_thesis_breakers.py investment_screener/backend/tests/py_services/test_daily_brief_thesis_breakers.py -v`
  — all green, no regressions in the existing `test_market_regime.py`/`test_risk_engine.py`
  suites either (run the full `py_services/` test directory once more before merge).
- Per `.agent/rules/worktree-subagent-isolation.md`: run `git status --short` in the **main
  checkout** (not the worktree) after every task, confirming no stray writes leaked outside
  the worktree.
