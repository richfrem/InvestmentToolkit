---
description: Rules for safe git operations — what requires explicit approval, what is forbidden without it.
globs: ["**/*"]
---

# Git Operations Policy

## Hard Rules (never violate)

### Worktree creation is mandatory, not a judgment call
Before any code, script, or multi-file content-authoring task, create a git worktree
(`superpowers:using-git-worktrees`, or `git worktree add` directly) **before starting work** — do
this every time, unconditionally. Never decide unilaterally that a task is "small enough" or "low
risk enough" to skip worktree creation and work directly in the shared main checkout instead. If
genuinely unsure whether a worktree is warranted for a given task, ask the user — don't decide
silently and proceed.

**Reason:** 2026-07-17 — an entire multi-sub-project phase of work (Phase 6: an `AGENTS.md` audit,
an eval-coverage backfill touching 53 files, a Questrade REST integration removal touching ~51
files including live-order fallback code, an agent relocation between plugins, and a new Python
script + test suite) was done directly on the shared main checkout and pushed straight to
`origin/main` every time, with zero worktree ever created — because each individual task was
separately judged "small enough" to skip it. This left no reviewable feature branch for any of it,
caused real confusion and rework reconciling local `main` vs. `origin/main` state after the fact,
and directly contradicted the project's own established Phase 1-5 pattern (worktree → review →
merge to local main → push). See `.agent/rules/worktree-subagent-isolation.md`'s "Failure Mode 2"
section for the full incident writeup.

A trivial single-line doc typo fix does not need this. Anything else — a bug fix, a new script, a
multi-file docs pass, an agent/skill relocation — does, regardless of how contained it looks.

### No git stash without explicit instruction
Never run `git stash`, `git stash pop`, or `git stash apply` unless the user explicitly says to.
**Reason:** A stash pop in a prior session applied content from an old unrelated stash onto the
current branch, introducing silent regressions. The risk is not worth it — there is always a
safer path.

### When a push is rejected
If `git push` is rejected because the remote is ahead:
1. Run `git pull --rebase` only (no stash).
2. If there are unstaged changes that block the rebase, **stop and tell the user** — do not stash.
3. Push after the rebase completes cleanly.
Never reach for stash as a shortcut around a rejected push.

### No force push to main/master
Never `git push --force` to main or master under any circumstances.

### No --no-verify
Never skip hooks with `--no-verify` unless the user explicitly requests it.

### Commit only what is asked
Do not commit files the user did not ask to commit. Auto-modified runtime files
(`plugin-sources.json`, `skills-lock.json`, `context/events.jsonl`) are noise — never commit them
unless explicitly asked.

## Approval Required

- Any `git reset` (hard or soft)
- Any `git rebase -i`
- Any branch deletion (`git branch -d` / `-D`)
- Any `git push --force-with-lease` or force variant
- Any `git clean`
- Committing files outside the scope of the current task

## Safe Without Asking

- `git status`, `git diff`, `git log` — read-only, always safe
- `git add <specific files>` + `git commit` when the user asked to commit
- `git push` (non-force) when the user asked to push
- `git pull --rebase` when a push is rejected (no stash)
- `git checkout -b <branch>` when the user asks for a new branch
