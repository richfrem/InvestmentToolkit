# Phase 6, Sub-Project 1 — AGENTS.md Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `AGENTS.md` (repo root) back into sync with what actually exists on disk under
`plugins/*/skills/` and `plugins/*/agents/`, closing every missing/stale/incomplete entry found.

**Architecture:** Docs-only change. No code, no tests in the pytest sense — the plan substitutes a
grep-based "ground truth vs. current doc" diff as the verification step, per the design spec's
framing (`docs/superpowers/specs/2026-07-15-phase6-agents-md-audit-design.md`). Two tasks: (1)
enumerate ground truth and classify every gap, (2) fix `AGENTS.md` and verify zero gaps remain.

**Tech Stack:** Bash (`find`, `grep`, `awk`), markdown editing. No new dependencies.

## Global Constraints

- Scope is `AGENTS.md` only — no other file may be modified except an optional one-line status
  note in `start_here.md` at the very end (per spec's Output section).
- Match `AGENTS.md`'s **existing format exactly**: agent entries get a one-line bold trigger +
  description + file path (same pattern as the current `daily-loop-agent`/`weekly-review-agent`
  entries) — no new "input artifact / output artifact" table format (explicit user decision during
  brainstorming).
- No skill/agent content may be deleted or edited — this plan only adds/corrects references
  *about* them inside `AGENTS.md`. Per `.agent/rules/skill-deletion-guard.md`, any suspected stale
  or superseded skill is out of scope here (that's sub-project 3, not started).
- Per this repo's git policy (`start_here.md` §"Git policy going forward"): commit to local `main`
  directly — no worktree needed for a docs-only change this small, no separate feature branch
  required, push straight to `origin/main` when done.

---

### Task 1: Ground-truth enumeration and gap classification

**Files:**
- Create (scratch, not committed): `/private/tmp/claude-501/-Users-richardfremmerlid-Projects-InvestmentToolkit/155fdf09-eae5-4419-93af-be9bf4d4faf6/scratchpad/skill_inventory.txt`
- Create (scratch, not committed): `/private/tmp/claude-501/-Users-richardfremmerlid-Projects-InvestmentToolkit/155fdf09-eae5-4419-93af-be9bf4d4faf6/scratchpad/agent_inventory.txt`
- Create (scratch, not committed): `/private/tmp/claude-501/-Users-richardfremmerlid-Projects-InvestmentToolkit/155fdf09-eae5-4419-93af-be9bf4d4faf6/scratchpad/gap_findings.md`
- Read: `AGENTS.md` (repo root)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `gap_findings.md` — a markdown list with three headed sections (`## Missing`, `##
  Stale`, `## Incomplete`), each entry formatted as `- **<plugin>/<name>** (`<path>`): <one-line
  reason>`. Task 2 reads this file directly to know what to add/fix in `AGENTS.md`.

- [ ] **Step 1: Enumerate every skill on disk with its plugin, frontmatter name, and trigger phrase**

Run:
```bash
SCRATCH=/private/tmp/claude-501/-Users-richardfremmerlid-Projects-InvestmentToolkit/155fdf09-eae5-4419-93af-be9bf4d4faf6/scratchpad
find plugins -name "SKILL.md" | sort | while read -r f; do
  plugin=$(echo "$f" | cut -d/ -f2)
  name=$(grep -m1 '^name:' "$f" | sed 's/^name: *//')
  echo "### $plugin / $name ($f)"
  grep -oE '/[a-zA-Z][a-zA-Z-]*' "$f" | sort -u | tr '\n' ' '
  echo
  echo
done > "$SCRATCH/skill_inventory.txt"
wc -l "$SCRATCH/skill_inventory.txt"
```
Expected: a non-empty file, one block per `SKILL.md` found (45 skills per the count established
during brainstorming), each block showing the plugin, the frontmatter `name:`, and every
`/slash-command`-shaped token found anywhere in the file (catches triggers mentioned in prose, not
just frontmatter).

- [ ] **Step 2: Enumerate every agent on disk with its plugin, frontmatter name, and trigger description**

Run:
```bash
SCRATCH=/private/tmp/claude-501/-Users-richardfremmerlid-Projects-InvestmentToolkit/155fdf09-eae5-4419-93af-be9bf4d4faf6/scratchpad
find plugins -path "*/agents/*.md" | sort | while read -r f; do
  plugin=$(echo "$f" | cut -d/ -f2)
  name=$(grep -m1 '^name:' "$f" | sed 's/^name: *//')
  echo "### $plugin / $name ($f)"
  awk '/^description:/{flag=1} flag{print} /^tools:|^dependencies:|^---$/{if(flag && !/^description:/) exit}' "$f" | head -8
  echo
done > "$SCRATCH/agent_inventory.txt"
wc -l "$SCRATCH/agent_inventory.txt"
```
Expected: a non-empty file with one block per `agents/*.md` file found (11 agents per the count
established during brainstorming), each block showing plugin, frontmatter `name:`, and the first
few lines of its `description:` field.

- [ ] **Step 3: Cross-reference each inventory entry against current `AGENTS.md` content and classify gaps**

Read `AGENTS.md` in full, then read `skill_inventory.txt` and `agent_inventory.txt` from Step 1/2.
For every entry in both inventories, check whether it (its `name:`, its slash-command trigger, or
a close textual match) appears anywhere in `AGENTS.md`. This is a manual judgment step, not a
scripted grep-only match — frontmatter `name:` fields sometimes use underscores
(e.g. `rebalance_portfolio` in `SKILL.md`) while `AGENTS.md` prose uses the hyphenated
slash-command form (e.g. `/rebalance-portfolio`), so an exact-string grep will produce false
positives; read for meaning, not just string equality.

Classify every discrepancy found into exactly one of three buckets and write the result to
`gap_findings.md`:
- **Missing** — skill/agent exists on disk, not mentioned anywhere in `AGENTS.md`. (7 agents
  already known from brainstorming: `risk-officer-agent`, `red-team-agent`, `data-quality-agent`,
  `thesis-review-agent`, `portfolio-advisor-orchestrator`, `single-stock-advisor`, `ta-guide` —
  confirm these plus find any additional missing skills.)
- **Stale** — an `AGENTS.md` entry references something renamed/removed/no-longer-accurate.
- **Incomplete** — an `AGENTS.md` entry exists but is missing a command/flag/detail the skill/agent
  now has that it didn't when the entry was written (e.g. compare `SKILL.md` body against what
  `AGENTS.md`'s one-line summary claims).

Write `gap_findings.md` with this exact structure:
```markdown
## Missing
- **portfolio-advisor/risk-officer-agent** (`plugins/portfolio-advisor/agents/risk-officer-agent.md`): not mentioned anywhere in AGENTS.md
- ...

## Stale
- **<plugin>/<name>** (`<path>`): <what's wrong>
- ...

## Incomplete
- **<plugin>/<name>** (`<path>`): <what's missing>
- ...
```
If a bucket has zero entries, keep its heading with a single line: `(none found)`.

Expected: `gap_findings.md` exists, is non-empty, and its `## Missing` section includes at minimum
the 7 already-known agents (confirms the enumeration approach didn't miss anything already
established during brainstorming — if any of the 7 is absent from the file, the cross-reference
step has a bug and must be redone before proceeding to Task 2).

- [ ] **Step 4: Verify the 7 known-missing agents are present in gap_findings.md**

Run:
```bash
SCRATCH=/private/tmp/claude-501/-Users-richardfremmerlid-Projects-InvestmentToolkit/155fdf09-eae5-4419-93af-be9bf4d4faf6/scratchpad
for a in risk-officer-agent red-team-agent data-quality-agent thesis-review-agent portfolio-advisor-orchestrator single-stock-advisor ta-guide; do
  grep -q "$a" "$SCRATCH/gap_findings.md" && echo "OK: $a" || echo "MISSING FROM FINDINGS: $a"
done
```
Expected: seven `OK:` lines, zero `MISSING FROM FINDINGS:` lines. If any line reads "MISSING FROM
FINDINGS", go back to Step 3 and add the missing entry before continuing.

- [ ] **Step 5: No commit for this task**

This task only produces scratch files outside the repo (in the session scratchpad, not
`/Users/richardfremmerlid/Projects/InvestmentToolkit`), so there is nothing to `git add` or commit.
Proceed directly to Task 2.

---

### Task 2: Apply fixes to AGENTS.md and verify

**Files:**
- Modify: `AGENTS.md` (repo root)
- Read: `gap_findings.md` (from Task 1, scratch path above)
- Modify (optional, only if Task 1 found nothing needing a broader note): `start_here.md`

**Interfaces:**
- Consumes: `gap_findings.md`'s three sections (Missing / Stale / Incomplete) produced by Task 1.
- Produces: an updated `AGENTS.md` with zero remaining gaps (verified in Step 3 below). Nothing
  downstream in this plan consumes this task's output — it's the terminal task.

- [ ] **Step 1: Fix every "Missing" entry**

For each entry in `gap_findings.md`'s `## Missing` section, add a new bullet to `AGENTS.md` under
the correct plugin's existing `###` section (e.g. all `portfolio-advisor` agents go under `### 1.
Portfolio Advisor`). Match the exact existing format. For example, the current file already has
this pattern for `daily-loop-agent` (line 34):

```markdown
- **`/daily`**: **The one daily command.** Interactive loop agent — portfolio freshness check → morning brief (macro regime, TA sweep, conviction scores, earnings) → ranked triage cards (one per holding, in urgency order) → trade execution → evolution log. Replaces the manual 10-step checklist. Agent: `plugins/portfolio-advisor/agents/daily-loop-agent.md`.
```

Follow this exact shape for each of the 7 known-missing agents (trigger phrase in bold if the
agent has one, one-line description drawn from its frontmatter `description:` field, ending with
`Agent: <path>.`). Do the same for any additional missing skills/agents Task 1 found beyond the 7.

- [ ] **Step 2: Fix every "Stale" and "Incomplete" entry**

For each entry in `gap_findings.md`'s `## Stale` section, correct or remove the inaccurate
reference in `AGENTS.md` (rename to match current reality, or remove if the thing no longer
exists). For each entry in `## Incomplete`, extend the existing bullet with the missing detail —
edit in place, don't duplicate the bullet.

If both sections read `(none found)`, skip this step — nothing to do.

- [ ] **Step 3: Re-run the ground-truth enumeration and confirm zero gaps remain**

Run:
```bash
SCRATCH=/private/tmp/claude-501/-Users-richardfremmerlid-Projects-InvestmentToolkit/155fdf09-eae5-4419-93af-be9bf4d4faf6/scratchpad
for a in risk-officer-agent red-team-agent data-quality-agent thesis-review-agent portfolio-advisor-orchestrator single-stock-advisor ta-guide; do
  grep -q "$a" AGENTS.md && echo "OK: $a now in AGENTS.md" || echo "STILL MISSING: $a"
done
```
Expected: seven `OK:` lines, zero `STILL MISSING:` lines. Then manually re-read `AGENTS.md`
alongside `gap_findings.md` one more time to confirm every Stale/Incomplete entry was actually
addressed (this is a judgment check, not scriptable — the point is confidence the doc now reflects
reality, not just that 7 specific strings are present).

If any check fails, go back to Step 1/2 and fix before proceeding.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "$(cat <<'EOF'
docs: audit and update AGENTS.md against actual plugins/ contents

Cross-referenced every SKILL.md and agents/*.md on disk against
AGENTS.md's routing guide. Added the 7 agents shipped in Phase 3
(risk-officer-agent, red-team-agent, data-quality-agent,
thesis-review-agent, portfolio-advisor-orchestrator,
single-stock-advisor, ta-guide) that were never documented, plus any
other drift found. Closes Phase 6 sub-project 1 (of 4 identified
during brainstorming).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git log -1 --stat
```
Expected: commit succeeds, `git log -1 --stat` shows exactly `AGENTS.md` (and, if touched,
`start_here.md`) changed.

- [ ] **Step 5: Push to origin/main**

Per this repo's standing git policy (push straight to `origin/main`, no separate PR-wait step):
```bash
git push origin main
git fetch origin
git log origin/main -1
```
Expected: push succeeds; `git log origin/main -1` shows the same commit SHA just created,
confirming the push landed.
