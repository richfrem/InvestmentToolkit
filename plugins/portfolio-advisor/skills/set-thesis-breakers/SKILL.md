---
name: set-thesis-breakers
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
  /update-stock-analysis produces a fresh thesis.
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
