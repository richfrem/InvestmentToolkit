---
description: Two related but distinct failure modes — (1) a subagent's pwd/git-branch confirmation does not guarantee its Edit/Write calls stay inside an assigned worktree, and (2) the controller itself may skip creating a worktree at all. Both need their own mandatory check.
globs: ["**/*"]
---

# Worktree/Subagent Isolation

## Failure Mode 1: Subagent Leaks Outside an Existing Worktree

## The Problem This Rule Solves

Dispatching an implementer or fix subagent into a `superpowers:subagent-driven-development`
worktree, with an explicit instruction to `cd` into the worktree path and confirm via
`pwd` / `git branch --show-current` before making any change, is the project's standard
isolation pattern. It has still failed **twice**:

1. **Phase 2b, Task 3** — an implementer committed a change onto the user's active
   main-checkout branch instead of its assigned worktree (documented informally in
   `start_here.md` at the time; caught by independently verifying `git log`/`readlink`
   after the subagent's report, not by the subagent noticing its own mistake).
2. **Phase 3 C2, Task 7 fix rounds (2026-07-09)** — a fix subagent left a stray,
   uncommitted, *incomplete* copy of its changes in the main checkout's
   `plugins/portfolio-advisor/scripts/daily_brief.py`, despite reporting a passing
   `pwd`/`git branch --show-current` confirmation at task start. Not caught until the
   final pre-merge `git status` check on the main checkout — logged as
   `.agent/map-debt.md`'s "subagent-driven-development implementer wrote to main
   checkout instead of worktree (2nd occurrence)" entry.

Both times the subagent's own confirmation step passed. Both times a stray write still
landed in the main checkout anyway.

## The Law

> **A `cd`-and-confirm step at task start is not evidence that every subsequent
> Edit/Write call in that session targets the confirmed directory.** `cd` only changes
> the *Bash tool's* persisted shell state — the Edit/Write/Read tools resolve on the
> exact absolute path parameter they're given, independent of any prior `cd`. Treat the
> confirmation step as a cheap first-line check, not a guarantee, and verify the
> **controller's own main checkout** after every task, not just the worktree.

## Non-Negotiables

1. **Every subagent-driven-development dispatch still gets the standard confirmation
   step.** Instruct the subagent to `cd` into the exact worktree path as its first
   action and confirm via `pwd` and `git branch --show-current` before editing anything.
   This remains necessary — it just isn't sufficient on its own.

2. **After every implementer or fix subagent reports back, the controller runs
   `git status --short` in the main checkout (not the worktree) before generating the
   review package.** This is the mandatory second check. It catches a leak within one
   task cycle — while it's still uncommitted and trivially discardable — instead of
   only surfacing at final-merge time, when it's had 5+ more tasks to compound or get
   tangled into review history.

   ```bash
   # From the main repo root, not the worktree:
   git status --short
   ```

   Any unexpected `M` entry that wasn't present before the task's dispatch is a leak.
   Diff it before touching anything (`git diff <path>`) — don't assume.

3. **A leak found this way is virtually always safe to discard, but verify first.**
   The signature of this exact failure mode is: the main checkout's stray diff is an
   *incomplete* or *superseded* subset of work that's already properly committed in the
   worktree branch (e.g. missing a later fix-round commit's changes). If the diff
   content matches that pattern, discard it via `git checkout -- <path>` in the main
   checkout before merging. If the diff contains anything that doesn't look like a
   partial duplicate of the worktree's own committed work — stop and investigate before
   discarding; it may be unrelated, real, uncommitted user work that predates the
   session (check the pre-session `git status` baseline first).

4. **Log a repeat occurrence, don't just re-fix it silently.** Per
   `.agent/rules/self-evolution-policy.md`'s Map Debt register: a `Repeat: YES` entry
   requires action on next encounter, not further deferral. A third occurrence of this
   exact failure mode should prompt investigating the harness-level root cause directly
   (e.g. checking whether a specific tool or dispatch pattern is the common thread)
   rather than only reapplying this same procedural mitigation a third time.

## Where This Applies

- Any `superpowers:subagent-driven-development` or `superpowers:executing-plans`
  session that dispatches implementer/fix subagents into an isolated worktree.
- Applies to every task in a plan, not just the first or last — the leak in the C2
  incident happened during a mid-plan fix round (Task 7's second fix dispatch), not at
  the boundaries.

---

## Failure Mode 2: Controller Never Creates the Worktree At All

### The Problem This Section Solves

Failure Mode 1 above assumes a worktree already exists and a subagent's write leaked outside it.
This is a different, upstream failure: the **controller** (not a subagent) decides, task by task,
that a piece of work is "small enough" or "low risk enough" to skip worktree creation entirely and
just work directly in the shared main checkout — then commits and pushes straight to `origin/main`.

**Occurrence 1 — Phase 6, entire phase (2026-07-16 to 2026-07-17).** Four sub-projects (an
`AGENTS.md` audit, an eval-coverage backfill across 53 files via `subagent-driven-development`, a
Questrade REST integration removal across ~51 files including live-order fallback code and a
frontend modal deletion, an agent relocation between plugins, and a new Python script + test
suite) were each individually judged low-risk enough to skip worktree creation, and were committed
directly onto the shared main checkout and pushed straight to `origin/main`, every time. Notably,
one of these sub-projects explicitly invoked `superpowers:subagent-driven-development`, whose own
documented required workflow dependencies list `superpowers:using-git-worktrees` — that
requirement was skipped too, not just the general policy.

**Why this matters, concretely, beyond "it's the documented policy":**
- There is no reviewable feature branch for any of it — the user cannot review a diff and merge it
  themselves; it is simply already in `main`'s history by the time they see it.
- A change later described as "small" (the `AGENTS.md` audit) can grow substantially mid-task (the
  Questrade removal ballooned from an assumed docs-labeling pass into a ~51-file full-stack code
  removal once real scope surfaced) — by which point work is already committed directly to `main`,
  with no isolation boundary to fall back to.
- Reconciling local `main` against `origin/main` after the fact (e.g. when a separately-created
  feature branch's PR gets merged on GitHub directly, or a `git pull` happens on the wrong branch)
  becomes genuinely confusing without the clean "one worktree, one branch, one merge" checkpoint
  the documented process provides.

### The Law

> **Worktree creation is not a risk assessment the controller performs per task — it is a fixed,
> unconditional step that happens before any code, script, or multi-file content change, every
> time.** The only exception is a genuinely trivial single-line documentation fix. Everything else
> — bug fixes, new scripts, multi-file docs passes, agent/skill relocations, eval-file authoring —
> gets a real worktree first, no exceptions based on how contained the task looks.

### Non-Negotiables

1. **Before starting any qualifying task, create the worktree first.** Use
   `superpowers:using-git-worktrees`, or `git worktree add <path> -b <branch>` directly. Do this
   even if the task looks like "just a docs edit" or "just one script" — the Questrade incident
   above is the concrete proof that scope assessments made before starting are unreliable.
2. **If `subagent-driven-development` or `executing-plans` is invoked, follow its own listed
   required workflow dependencies without skipping any of them** — in particular
   `superpowers:using-git-worktrees`. Do not treat a skill's documented dependency list as
   optional because the task feels small.
3. **When in doubt, ask the user** whether a worktree is warranted for a specific task, rather than
   deciding silently and proceeding directly on the main checkout.
4. **The completion sequence is always: work in the worktree → whole-branch review → merge the
   worktree's branch into local `main` → push local `main` to `origin/main`.** There is no valid
   sequence where work lands as commits directly on the main checkout's `main` branch.

### Where This Applies

- Every task that isn't a single trivial documentation line-edit, regardless of the plugin,
  sub-project, or perceived size.
- Applies before `subagent-driven-development`/`executing-plans` is even invoked, not just within
  them — the worktree must exist first, before any implementer subagent is dispatched into it.
