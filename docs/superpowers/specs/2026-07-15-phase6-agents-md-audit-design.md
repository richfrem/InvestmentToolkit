# Phase 6, Sub-Project 1 — AGENTS.md Audit — Design

_Date: 2026-07-15_

## Context

`start_here.md` names Phase 6 ("skills/sub-agent architecture cleanup") as the last phase of the
Fable5 roadmap, with zero prior scoping — no spec, no plan, not even brainstormed before this
session. Brainstorming with the user surfaced four independent candidate pieces: (1) eval coverage
backfill for skills/agents with none, (2) an `AGENTS.md` accuracy audit, (3) dead/superseded skill
pruning, and (4) speculative reward-modeling groundwork on `orders_executed.jsonl`. These do not
share an architecture and were explicitly decomposed into separate sub-projects, each getting its
own spec → plan → implementation cycle. The user chose to tackle the `AGENTS.md` audit first
(fastest, lowest risk, and its findings may surface additional skills/agents relevant to the eval
backfill that comes next).

This spec covers **only** the `AGENTS.md` audit. The other three pieces remain queued in
`start_here.md` for their own future brainstorming sessions — out of scope here.

## Problem

`AGENTS.md` (repo root, 160 lines) is the curated agentic routing guide referenced by
`.agent/rules/` and used by any AI agent operating in this repo to find the right skill/agent for a
task. It was last meaningfully touched before Phase 3's G2 sub-spec shipped three new agents
(`risk-officer-agent`, `red-team-agent`, `data-quality-agent`), and none of those three — nor
`thesis-review-agent`, `portfolio-advisor-orchestrator`, `single-stock-advisor`, or `ta-guide` —
currently appear in the document at all. This was flagged as a known gap when Phase 3 closed out
and never acted on. The document may have other, currently-unknown drift from the same cause:
skills/commands added or renamed across Phases 3-5 without a corresponding `AGENTS.md` update.

## Approach

Direct grep-based audit + in-place edit. No subagent dispatch (this is a single, well-bounded
documentation task — dispatching would add indirection with no benefit). No structural rewrite of
`AGENTS.md` (its current per-plugin narrative structure works; this is a content-accuracy pass, not
a redesign — restructuring would be unrelated scope creep).

**Alternatives considered and dismissed:**
- *Subagent dispatch* — overkill for one 160-line doc with no TDD-gated implementation steps.
- *Full structural rewrite* (e.g. splitting into a dedicated Skills table + Agents table) — YAGNI;
  not requested, and the existing per-plugin prose format is what every prior phase's entries
  already follow. If the audit reveals the current structure genuinely can't represent something
  (unlikely), note it as a follow-up rather than restructuring mid-audit.

## Scope

`AGENTS.md` only. No code changes. Possibly a one-line status update in `start_here.md` marking
this sub-project done, matching the pattern every other completed phase/sub-spec in that file
already follows.

## Method

1. **Build ground truth.** For every plugin directory under `plugins/`, enumerate:
   - Every skill's `SKILL.md` — its slash-command trigger(s) and one-line purpose (frontmatter
     `description` + any `/command` name referenced in the body).
   - Every `agents/*.md` file — its trigger description and file path.
2. **Diff against `AGENTS.md`'s current content**, section by section (the doc is already organized
   by plugin — `Portfolio Advisor`, `Stock Valuation Analyst`, `ETF Analysis`, `TradingView
   Integration`, `Toolkit Manager`, plus the two dedicated onboarding-agent entry points at the
   top). Classify every discrepancy found into exactly one of three types:
   - **Missing** — a skill or agent that exists on disk but isn't mentioned anywhere in
     `AGENTS.md`. (7 agents already confirmed missing this way during brainstorming:
     `risk-officer-agent`, `red-team-agent`, `data-quality-agent`, `thesis-review-agent`,
     `portfolio-advisor-orchestrator`, `single-stock-advisor`, `ta-guide`.)
   - **Stale** — an entry in `AGENTS.md` that references something renamed, moved, or removed since
     the doc was last edited.
   - **Incomplete** — an entry that exists but is missing a command/flag/detail added to that
     skill/agent after the entry was originally written.
3. **Fix every gap in place**, matching the existing format exactly:
   - Agent entries: one-line **trigger phrase** (bold) + description + agent file path — same
     pattern as the current `daily-loop-agent`/`weekly-review-agent` entries (per the user's
     explicit choice during brainstorming: match existing style, not a new
     input-artifact/output-artifact contract format).
   - Skill/command entries: same bullet format already used under each plugin's `###` heading
     (trigger, one-line description, occasional script/path callout where the existing doc already
     does that).
4. **Verify.** Re-run the ground-truth enumeration from step 1 after editing and confirm every
   skill and agent found on disk is referenced somewhere in the updated `AGENTS.md`. This stands in
   for a test suite on a docs-only change — the "pass condition" is zero unreferenced items.

## Output

An updated `AGENTS.md`, committed to git with a message describing the audit and what was added.
No new files created. This closes sub-project 1 of the 4 identified during brainstorming; the
other three (eval coverage backfill, dead/superseded skill pruning, reward-modeling groundwork)
remain queued in `start_here.md`, each requiring its own brainstorming session before any
implementation.

## Out of Scope

- Any change to eval coverage (`evals/evals.json` files) — that's sub-project 2.
- Any deletion or flagging of stale skill *content* (skill bodies, not `AGENTS.md` entries about
  them) — that's sub-project 3, and per `.agent/rules/skill-deletion-guard.md`, deletions require
  explicit per-item user confirmation regardless.
- Reward-modeling / `orders_executed.jsonl` analysis — that's sub-project 4, entirely undesigned.
- Restructuring `AGENTS.md`'s format or organization.
