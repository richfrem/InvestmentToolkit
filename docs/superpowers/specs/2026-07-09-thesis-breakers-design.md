# B5 — Thesis Breakers (Fable5 Elevation Guide, Phase 3 Sub-Spec 3 of 5)

**Status:** Design — pending user review
**Date:** 2026-07-09
**Depends on:** E1 (`risk_engine.py` / `risk_snapshot.json`), C2 (`market_regime.py`, per-ticker
`trend`/`momentumPercentile`/`volatilityPercentile`) — both shipped on local `main`.
**Guide reference:** §3 B5 ("Thesis breakers as data, not prose"), §9 Phase 3 acceptance criteria.

## 1. Goal

The investment framework mandates "3 specific, measurable thesis breakers" per holding, but
today they only exist as prose inside `thesisForInclusion`. Nobody — human or agent — checks
them systematically. B5 makes them structured data: a `thesisBreakers` schema on each holding,
a CLI to author them, an evaluation engine that checks the automatable ones daily and tracks
the manual ones for staleness, and a triage integration that puts a `TRIGGERED` breaker at the
very top of `/daily` — above macro/regime/risk context and above every TA-signal-driven section.

**Phase 3 acceptance criterion this satisfies:** "a fixture triggered thesis-breaker appears at
top of triage."

## 2. Data model

### 2.1 Breaker definitions — `target-portfolio.json` (human-owned)

Each holding gains an optional `thesisBreakers` array:

```json
"thesisBreakers": [
  {
    "id": "nbis-trend-breakdown",
    "type": "auto",
    "metric": "trendState",
    "operator": "in",
    "threshold": ["DOWNTREND"],
    "horizon": 5,
    "note": "Sustained downtrend contradicts the GPU-cloud growth thesis"
  },
  {
    "id": "nbis-ndr-floor",
    "type": "manual",
    "metric": "ndr",
    "operator": "<",
    "threshold": 115,
    "horizon": "2 quarters",
    "note": "Net dollar retention floor from 10-Q disclosures",
    "status": "OK",
    "statusSetAt": "2026-07-01",
    "statusSetBy": "agent",
    "reviewCadenceDays": 90
  }
]
```

Field rules:

| Field | `type: "auto"` | `type: "manual"` |
|---|---|---|
| `metric` | must be one of the fixed enum (§2.3) | any descriptive string |
| `operator` | `<` `<=` `>` `>=` `==` `in` | same |
| `threshold` | number, or array for `in` | number, string, or array |
| `horizon` | integer — consecutive evaluated `/daily` runs (§3.2) | free text, documentation only, not evaluated |
| `status` | not stored here — lives in `thesis_breaker_state.json` (§2.2) | required: `OK` \| `WATCHING` \| `TRIGGERED` |
| `statusSetAt` / `statusSetBy` | n/a | required alongside `status` |
| `reviewCadenceDays` | n/a | required, default 45 if the authoring skill doesn't get an explicit answer |

`id` is unique per holding, kebab-case by convention. This file stays human-curated: writes go
through `update_thesis.py`'s existing versioned/diffed `save_thesis()` path (weight-sum
validation, `changeLog` note). Nothing automated mutates it — same boundary E1 and C2 already
respect (neither writes back into `target-portfolio.json`).

### 2.2 Evaluated state — new `data/thesis_breaker_state.json` (machine-owned)

Rewritten by `daily_brief.py`'s evaluation step every run, one entry per `(ticker, breakerId)`:

```json
{
  "generatedAt": "2026-07-09T13:00:00Z",
  "holdings": {
    "NBIS": {
      "nbis-trend-breakdown": {
        "type": "auto",
        "currentValue": "DOWNTREND",
        "conditionMet": true,
        "currentStreak": 3,
        "streakStartDate": "2026-07-07",
        "lastEvaluatedAt": "2026-07-09T13:00:00Z",
        "status": "WATCHING"
      },
      "nbis-ndr-floor": {
        "type": "manual",
        "status": "OK",
        "statusSetAt": "2026-07-01",
        "reviewCadenceDays": 90,
        "daysSinceReview": 8,
        "stale": false
      }
    }
  }
}
```

This mirrors the `risk_snapshot.json` / embedded `market_regime` pattern: definitions are
static and human-reviewed, state is dynamic and machine-computed, and the two never collide.

### 2.3 Auto metric enum (v1)

Resolved from data `daily_brief.py` already computes this run — no new fetches:

| `metric` | Source |
|---|---|
| `rsi` | conviction score row, `s["rsi"]` |
| `dcfFairValueGapPct` | conviction score row, `s["pct_to_fv"]` |
| `trendState` | `market_regime`'s per-ticker `tickerRegimes[].trend.state` (C2's `classify_ticker_trend`) |
| `momentumPercentile` | `market_regime`'s per-ticker `tickerRegimes[].momentumPercentile` (C2) |
| `pillarAvgScore` | `pillar_health` for the holding's `pillarId`, `.avg_score` |

If a value can't be resolved (ticker missing from `market_regime`'s output, `market_regime`
computation failed that run, etc.), `conditionMet` is `false` for that run — never crashes, never
false-triggers.

## 3. Evaluation engine — `py_services/thesis_breakers.py`

New script, same shape as `market_regime.py`/`risk_engine.py`: pure functions + an
importable/CLI orchestrator, wired into `daily_brief.py`.

### 3.1 Functions

- `evaluate_condition(value, operator, threshold) -> bool`
- `resolve_auto_metric_value(metric, ticker, conviction_scores, market_regime, pillar_health, target_data) -> Any | None`
- `evaluate_breakers(target_data, conviction_scores, market_regime, pillar_health, prev_state) -> dict`
  — pure function: takes the previous state dict and this run's already-computed inputs, returns
  the new state dict. No I/O — fully unit-testable on fixtures.
- `compute_breaker_state(target_portfolio_path=..., state_path=...) -> dict` — I/O wrapper: loads
  both JSON files, calls `evaluate_breakers`, writes the new state file, returns
  `(state_dict, newly_triggered: list[dict])`.
- `log_breaker_override(ticker, breaker_id, rationale, snapshot) -> None` — appends one line to
  `data/theses/breaker-overrides.jsonl` (§5).

### 3.2 Streak semantics (resolves the horizon-underspecification gap)

No historical time series of RSI/trend/DCF-gap exists per ticker per day, and adding one is out
of scope for this sub-spec. So `horizon` counts **consecutive `/daily` runs in which the breaker
was evaluated**, not consecutive calendar days:

- Each run, `conditionMet` is computed fresh from this run's data.
- `currentStreak` increments when `conditionMet` is `true`, resets to `0` (and clears
  `streakStartDate`) when `false`.
- `status` = `WATCHING` while `0 < currentStreak < horizon`, `TRIGGERED` once
  `currentStreak >= horizon`.
- A skipped `/daily` run (weekend, TV offline) just means the next run is still "the next
  consecutive check" — the streak advances slower than horizon implies, it never falsely
  triggers or resets from a calendar gap.

This intentionally does **not** couple to `context/events.jsonl` — that file is the Agentic OS
plugin's own cross-plugin event bus (`post_run_hook`/`session_summary` entries), unrelated to
portfolio domain data, and coupling to it would cross the plugin-isolation rule (CLAUDE.md #5).
`thesis_breaker_state.json`'s own `lastEvaluatedAt`/`currentStreak` fields are the complete
record of "checks" — no second log needed.

### 3.3 Manual breaker staleness

`stale = today > statusSetAt + reviewCadenceDays`. Surfaced in triage as a low-urgency note
(distinct from `TRIGGERED`) — a stale manual assessment is "needs a fresh look," not "thesis
broken." `reviewCadenceDays` is captured per-breaker at authoring time by the
`set-thesis-breakers` skill (§6), not a global constant.

## 4. `daily_brief.py` integration

`run()`: after `scores_raw`, `market_regime`, and `pillars` are computed (already happens
earlier in the pipeline — no duplicate fetches), call `compute_breaker_state()` and add
`brief["thesis_breakers"] = state` plus `brief["thesis_breakers_triggered"] = newly_triggered`.

`render()`: if any breaker has `status == "TRIGGERED"` (auto or manual), render a block
**immediately after the header, before the overnight-gaps section** — literally the first
content in the brief, satisfying "top of triage, above all TA signals":

```
🚨  THESIS BREAKER TRIGGERED — 1 holding:
    NBIS  trendState in [DOWNTREND]  (current: DOWNTREND, 5/5 consecutive runs)
          "Sustained downtrend contradicts the GPU-cloud growth thesis"
```

Sorted by holding `targetWeight` descending (largest positions surface first). Stale manual
breakers render as a smaller note further down, near pillar health — informational, not urgent.

**Standing-decision interaction (explicit, per guide §10.3):** a `TRIGGERED` breaker escalates
*visibility* only — it moves to the top of the brief — never *authority*. It cannot flip
`aiThesis.action` or bypass `standingDecision`, identical to how existing EXIT/REDUCE bands
already downgrade to `"HOLD"` with `"Signal stands but no trade proposed without your
direction"` in `brief_recommendations.py` when a standing decision exists. A `dcfFairValueGapPct`
breaker in particular does not gain override power over the >15%-material-delta gate — it is a
second notification path into the same human-in-the-loop confirmation, not a competing gate.

## 5. Override logging — accountability trail

`investment_screener/backend/data/theses/breaker-overrides.jsonl` (append-only, co-located with
`target-portfolio.json`). Written by the daily-loop-agent (not by `daily_brief.py` itself — only
a human decision constitutes an "override") when the user reviews a `TRIGGERED` breaker card and
chooses to hold anyway, via `log_breaker_override()`:

```json
{"date":"2026-07-09","ticker":"NBIS","breakerId":"nbis-trend-breakdown","metric":"trendState","currentValue":"DOWNTREND","threshold":["DOWNTREND"],"streak":5,"horizon":5,"rationale":"Vera Rubin ramp de-risks the downtrend; holding through","overriddenBy":"user"}
```

## 6. `set-thesis-breakers` skill — interactive, HITL authoring

Raw `update_thesis.py --set-breaker '{...}'` JSON is the **machine interface** — an expert
escape hatch, not how anyone should author "the 3 conditions that would make me sell." A new
skill wraps it, same shape as `calibrate-targets` (`plugins/portfolio-advisor/skills/set-thesis-breakers/`
— `SKILL.md` + `scripts/`), and the same collaborative-but-opinionated persona style.

**Trigger:** `/set-thesis-breakers {TICKER}`; also auto-suggested as the natural next step at the
end of `/evaluate-stock`'s output (a pointer added to `stock_valuation`'s closing summary).

**HITL is the point of this skill, not an afterthought:** every breaker gets written only after
the user has seen it explained in plain language and explicitly confirmed it — never a silent
default, never inferred and saved without a turn where the user can reject or rewrite it. This
mirrors Standing Constraint §10.1 ("HITL is sacred") applied to thesis authorship, not just trade
execution.

**Flow (one question at a time, matching the daily-loop/calibrate-targets convention):**

1. Read the holding's `thesisForInclusion` rationale, `analyticsLog.{framework,peerBench,technicals}`
   (Phase 2b), DCF scenario params, `aiThesis` — before asking anything.
2. Derive 2–3 *candidate* breakers from what's already in the rationale (e.g. a cited NDR floor,
   a margin-expansion claim) instead of a blank-page ask.
3. Per candidate, ask: keep as proposed / edit threshold / reject / write your own.
4. Classify each as `auto` or `manual` and explain the tradeoff in plain language — this is the
   moment the auto/manual distinction becomes legible to the user, not a hidden schema detail:
   *"This one needs you to check in — I can't watch NDR automatically, so I'll flag it for review
   every N days instead of catching it live."*
5. For `auto` breakers, state the horizon honestly: *"needs 5 consecutive daily runs to confirm
   — it won't fire on a single bad day."*
6. For `manual` breakers, capture `reviewCadenceDays` conversationally: *"I'll remind you to
   revisit this every ~45 days — right, or does this need checking more often?"*
7. Soft-nudge toward 3 total breakers (warn if fewer than 2 are set by the end of the session;
   never hard-block — some theses genuinely have 2 clean breakers, not 3).
8. Confirm each breaker in plain English, then call `update_thesis.py --set-breaker` under the
   hood. The user never sees or writes raw JSON.

Editing an existing breaker (pre- or post-commit) goes through this same conversational loop —
no dedicated `--edit-breaker` CLI flag. Post-commit edits call `--remove-breaker` then
`--set-breaker` back to back under the hood, invisible to the user as two calls.

## 7. Non-goals / explicitly deferred

- **Backfilling real breaker data for the 73 existing holdings.** This sub-spec ships schema +
  CLI + engine + skill, verified on fixtures — matching the Phase 3 acceptance criterion
  ("a fixture triggered thesis-breaker appears at top of triage"), not full portfolio coverage.
  Populating real holdings is natural follow-up work for `thesis-review-agent` or a dedicated
  backfill pass.
- **A historical time-series store** for auto metrics. Streak tracking works entirely off the
  persisted run-based counter (§3.2); no new data-layer capability is required.
- **`--edit-breaker` CLI flag.** Superseded by the skill's conversational edit loop (§6).
- **Any auto-execution of trades from a `TRIGGERED` breaker.** Visibility escalation only —
  Standing Constraint §10.1 (HITL is sacred) applies without exception.

## 8. Testing plan (TDD — failing test first, per repo convention)

`investment_screener/backend/tests/py_services/test_thesis_breakers.py`:

- `evaluate_condition()` for every operator, including boundaries (`>=`/`<=` exact-threshold
  match, `in` against a list, `==` for categorical).
- Streak progression: 3 consecutive `true` evaluations against `horizon: 5` → `WATCHING`;
  the 5th → `TRIGGERED`.
- Streak reset: `true, true, false, true` → streak is `1` after the 4th run, not `3`.
- Manual staleness: `stale` computed correctly from `statusSetAt + reviewCadenceDays` vs. an
  injectable "today" (no wall-clock coupling in the test).
- `resolve_auto_metric_value()` for all 5 enum metrics, plus the missing-data case (ticker absent
  from `market_regime` output → `None`, `conditionMet` is `false`, no exception).
- `compute_breaker_state()` end-to-end fixture: prior state at streak 4/5 + this run's condition
  still `true` → new state is `TRIGGERED`, file round-trips correctly.
- `log_breaker_override()`: appends one well-formed JSONL line, doesn't clobber existing lines.

CLI tests (wherever `update_thesis.py` is currently tested, or a new
`test_update_thesis_breakers.py` alongside it): `auto` metric restricted to the enum, `threshold`
type must match `operator` (list required for `in`), `id` uniqueness enforced per holding,
`--remove-breaker` round-trips through `save_thesis()`.

`daily_brief.py` render test: fixture brief with one `TRIGGERED` breaker asserts it appears
before the overnight-gaps line and before any REDUCE/ACCUMULATE section — the literal Phase 3
acceptance criterion.

## 9. Standing constraints checklist

1. HITL is sacred — §4 (visibility not authority), §6 (skill never silently writes).
2. Decision support, not advice — brief renders analysis, human decides; no new automated writes.
3. `standingDecision` anchor semantics unchanged — §4 explicit.
4. No silent schema breaks — `thesisBreakers` is a new optional field (additive), new
   `thesis_breaker_state.json` is a new file (no migration needed).
5. Reproducibility over cleverness — streak state is fully persisted and inspectable, not
   inferred from unlogged history.
6. Provider terms — n/a, no new external data source.
