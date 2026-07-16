# Phase 6, Sub-Project 2 — Eval Coverage Backfill — Design

_Date: 2026-07-16_

## Context

`start_here.md` names eval coverage as the most concrete, explicitly-named Phase 6 item ("G3...
filling skill evals is explicit Phase 6 scope"). As of this session (post-Questrade-archive, which
removed `questrade-token-setup` from the count): **44 total skills**, of which 39 have zero eval
coverage, 2 (`calibrate-targets`, `set-thesis-breakers`) are empty scaffolds (`{"evals": []}`), and
1 (`run-screener`) uses a lightweight simple schema. **11 agents have zero eval coverage** — no
agent in this repo has ever had an eval file. Two skills already have rich coverage and serve as
the template: `stock_valuation` (8 evals) and `portfolio-health` (8 evals).

This spec covers only eval coverage. It does not touch skill/agent content, routing, or the
broader "dead/superseded skill pruning" and "reward-modeling groundwork" sub-projects, which remain
separately queued.

## Schema

Every new or upgraded eval file uses the rich schema already established by `stock_valuation` and
`portfolio-health`:

```json
{
    "skill": "<skill_or_agent_name>",
    "version": "1.0.0",
    "description": "Benchmark evaluation suite for trigger accuracy, schema compliance, and adversarial robustness of the <name> skill.",
    "scoring_version": "v2.0",
    "evals": [
        { "id": "EVAL-001", "type": "positive", "category": "trigger", "prompt": "...", "expected_trigger": "...", "pass_condition": "..." },
        { "id": "EVAL-002", "type": "positive", "category": "schema_compliance", ... },
        { "id": "EVAL-003", "type": "positive", "category": "standalone_degradation", ... },
        { "id": "EVAL-004", "type": "negative", "category": "hallucination", ... },
        { "id": "EVAL-005", "type": "negative", "category": "sycophancy", ... },
        { "id": "EVAL-006", "type": "near_miss", "category": "trigger_conflict", "expected_trigger": "<the other skill/agent>", "expected_not_trigger": ["<this skill>"], ... },
        { "id": "EVAL-007", "type": "near_miss", "category": "schema_type_error", ... }
    ],
    "benchmark_targets": {
        "trigger_accuracy": "≥ 90% of trigger-category evals pass",
        "schema_compliance": "100% of schema_compliance evals pass"
    }
}
```

Not every category applies to every target — a read-only chart-control skill (`tv-add-indicator`)
has no meaningful "sycophancy" scenario, and an internal-only skill (`ta-red-team`, never directly
user-triggered) has no meaningful "trigger" category at all. **Each eval file uses the categories
that genuinely apply to its target, not a mechanically-copied 7-slot template** — a minimum of 4
evals per file (trigger-or-equivalent, schema/output-shape, one negative case, one near-miss or
edge case), scaling up to 8 for complex/high-stakes targets (order placement, valuation, risk
gates).

## Agent Eval Location (new convention)

Agents are flat files (`plugins/<plugin>/agents/<agent-name>.md`), unlike skills which each have
their own folder. No prior eval convention exists for agents. This spec establishes:
`plugins/<plugin>/agents/evals/<agent-name>.json` — one shared `evals/` directory per plugin's
`agents/` folder, one JSON file per agent, same schema as skill evals above (with `"skill"` field
repurposed to hold the agent name — no schema fork needed).

## Scope — 53 targets

**39 skills with zero eval coverage** (full list obtainable via `find plugins -name "SKILL.md" |
while read f; do d=$(dirname "$f"); [ -f "$d/evals/evals.json" ] || echo "$d"; done`), spanning:
- `etf-analysis`: 1 (`etf_analysis`)
- `stock-valuation`: 3 (`stock-research`, `forward-valuation-challenge`, `valuation-math-validation`)
- `portfolio-advisor`: ~13 (`rebalance-portfolio`, `x-news-sweep`, `daily-loop`, `daily-brief`,
  `adversarial-review`, `thesis-challenge-bundler`, `norberts-gambit`, `strategic-review`,
  `thesis-review`, `13f-analyze`, `13f-tracker`, `update-portfolio-targets`, `ytd-return`)
- `tradingview`: ~22 (`place-order`, `modify-order`, `cancel-order`, `get-orders`, `alert-list`,
  `alert-sync`, `pine-inject`, `author-pine-script`, `tv-portfolio-sync`, `tv-price-refresh`,
  `tv-manage-watchlists`, `chart-snapshot`, `ta-snapshot`, `ta-red-team`,
  `technical-analysis-expert`, `tv-add-indicator`, `tv-change-symbol`, `tv-change-type`,
  `tv-chart-setup`, `tv-save-indicator`, `tv-setup`, `ta-daily-sweep`)

**2 empty scaffolds to fill:** `portfolio-advisor/skills/calibrate-targets`,
`portfolio-advisor/skills/set-thesis-breakers`.

**1 simple-schema file to upgrade:** `toolkit-manager/skills/run-screener` (currently a flat
3-eval list, no `benchmark_targets` — rewrite to the rich schema).

**11 agents with zero eval coverage:** `portfolio-advisor/agents/{daily-loop-agent,
data-quality-agent, portfolio-advisor-orchestrator, red-team-agent, risk-officer-agent,
single-stock-advisor, thesis-review-agent, weekly-review-agent}`,
`toolkit-manager/agents/{toolkit-onboarding-guide, tradingview-onboarding}`,
`tradingview/agents/ta-guide`.

## Method

Each eval file is authored by reading its target's actual `SKILL.md`/`agent.md` content
(frontmatter `description`, trigger conditions, dependencies, hard rules/gates it documents) to
derive realistic scenarios specific to that target's domain — not templated boilerplate copied
across all 53 files. A DCF-valuation skill's near-miss case looks nothing like a CDP
chart-control skill's near-miss case.

## Execution

`subagent-driven-development`, batched by plugin (~7 tasks): `etf-analysis` (1 file),
`stock-valuation` (3 new + reuse of existing `stock_valuation` template knowledge, 3 files),
`toolkit-manager` (1 skill upgrade + 2 agent files, 3 files), `portfolio-advisor` split into two
batches (~13 skills + 8 agents = 21 files across 2 tasks), `tradingview` split into two batches
(~22 skills + 1 agent = 23 files across 2 tasks). Each task's subagent reads its assigned
targets' actual files before writing evals — no task may write an eval file for a skill it hasn't
read.

## Verification

No automated test suite applies to eval *content* quality (these are benchmark specs consumed by
a human or a future eval-runner, not executable code). Verification is structural, per file:
1. Valid JSON (parses without error).
2. Required top-level fields present (`skill`, `version`, `description`, `scoring_version`,
   `evals`, `benchmark_targets`).
3. Every eval entry has `id`, `type`, `category`, `prompt`, and either `expected_trigger` (or
   `expected_not_trigger` for near-miss) and `pass_condition`.
4. At least 4 eval entries per file.
5. Final count: all 53 targets have a populated (non-empty-array) `evals.json`.

## Out of Scope

- Building an actual eval-*runner* (a harness that executes these prompts against a live agent and
  scores pass/fail) — this spec only produces the eval *specifications*, matching the current state
  of the 5 existing filled examples (none of which have a runner either).
- Any change to skill/agent behavior, routing, or content.
- The other two Phase 6 sub-projects (dead/superseded skill pruning, reward-modeling groundwork).
