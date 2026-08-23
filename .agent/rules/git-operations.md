---
description: Rules for safe git operations — what requires explicit approval, what is forbidden without it.
globs: ["**/*"]
---

# Git Operations Policy

## 5-Step Standard Feature Branch & Post-Merge Protocol (No Guessing, No Resetting)

Always follow this exact 5-step cycle for every code change:

```bash
# 1. Implement, commit, and push directly to origin feature branch:
git checkout -b chore/feature-name
# (make edits)
git add <files>
git commit -m "feat: description"
git push -u origin chore/feature-name

# 2. User opens PR and merges it into main on GitHub.

# 3. User says "I merged the PR". You checkout main:
git checkout main

# 4. Pull origin/main cleanly (enforced fast-forward only):
git pull origin main

# 5. Delete merged feature branch locally and remotely:
git branch -d chore/feature-name
git push origin --delete chore/feature-name
```

### Git Defaults Enforced:
- Repository MUST have `git config pull.ff only` configured.
- NEVER run `git reset --hard`, `git push --force`, or unprompted merge aborts. If `git pull origin main` fails fast-forward, stop and report the exact state to the user.

---

## Hard Rules (never violate)

### Worktree creation is mandatory, not a judgment call
Before any code, script, or multi-file content-authoring task, create a git worktree
(`superpowers:using-git-worktrees`, or `git worktree add` directly) **before starting work** — do
this every time, unconditionally. Never decide unilaterally that a task is "small enough" or "low
risk enough" to skip worktree creation and work directly in the shared main checkout instead. If
genuinely unsure whether a worktree is warranted for a given task, ask the user — don't decide
silently and proceed.

**Reason:** 2026-07-17 — an entire multi-sub-project phase of work (Phase 6: an `AGENTS.md` audit,
an eval-coverage backfill touching 53 files, a legacy broker REST integration removal touching ~51
files including live-order fallback code, an agent relocation between plugins, and a new Python
script + test suite) was done directly on the shared main checkout and pushed straight to
`origin/main` every time, with zero worktree ever created — because each individual task was
separately judged "small enough" to skip it. This left no reviewable feature branch for any of it,
caused real confusion and rework reconciling local `main` vs. `origin/main` state after the fact,
and directly contradicted the project's own established Phase 1-5 pattern (worktree → review →
merge to local main → push). See `.agent/rules/worktree-subagent-isolation.md`'s "Failure Mode 2"
section for the full incident writeup.

**The actual boundary:** pure documentation/markdown edits (rule files, specs, plans, READMEs) never
need a worktree, regardless of file count — commit those directly. Anything touching real code —
Python, TypeScript, JS, executable scripts, config that changes runtime behavior — needs a worktree,
especially anything substantial enough to warrant `subagent-driven-development`. When a worktree is
used, follow the full protocol properly (worktree → work → review → merge to local main → push) —
not a shortcut where work happens in the main checkout first and gets relabeled as a branch after
the fact.

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

## End-of-Wave Closeout Playbook (mandatory sequence, do not improvise per-wave)

**Reason:** 2026-07-22 — closing out Wave 3 of the Domain Data Model v3.2 migration required two
separate PR rounds, two accidental direct-to-main commits (caught and corrected each time via
reset+cherry-pick), and two rounds of manually-resolved merge conflicts in the same class of
auto-generated files — all because this sequence was re-derived by hand under pressure instead of
followed as a fixed checklist. Every step below is now the required order; skipping or reordering
steps is what caused the friction.

1. **Do the full final verification sweep BEFORE the first push, not after.** If a wave's own
   discipline includes a repo-wide grep/consumer-inventory check (see
   `docs/superpowers/plans/*-implementation-plan.md` for the pattern), run it to completion and
   resolve every real finding *before* opening a PR — not iteratively, discovering "one more real
   consumer" after a PR is already merged. A second PR for stragglers is real rework, not a normal
   part of the process.
2. **Never run live, data-mutating operations (real broker syncs, real price refreshes, real
   trades) inside a feature worktree**, especially not after that worktree's PR has already been
   opened or merged. A feature worktree holds code changes for review; live data belongs on `main`
   or wherever the running app's real state lives. Running a live sync inside the worktree is what
   produced extra, un-reviewed commits *after* the PR merged, forcing a second cherry-pick/PR round
   to recover them. If live validation against real data is genuinely needed mid-wave, do it from
   the main checkout (or a disposable scratch copy), read-only where possible, and only commit
   real resulting data changes as an explicit, separate step — not as a side effect of testing.
3. **Before any `git commit` while wave work is in progress, confirm `pwd` first.** Two commits
   this session landed on `main` by mistake (a report file, a Map Debt entry) because the shell's
   cwd had silently reset to the main checkout between tool calls. The fix is procedural, not
   tooling: run `pwd` (or check the command's own `cwd` context) immediately before any `git add`/
   `git commit` whose content belongs in a worktree, and cd back explicitly if it doesn't match.
4. **Auto-generated/regenerated content (thesis docs, `AUTO_UPDATE_START/END` blocks, any file a
   sync script rewrites wholesale) will conflict on every merge that spans a sync run — this is
   expected, not a surprise to re-diagnose each time.** The resolution rule is: keep the side with
   the later timestamp / more complete real data (a `$0`/all-zero regenerated snapshot is a broken
   or partial sync, never preferred over a populated one, regardless of which side of the merge it's
   on). Hand-authored prose fields (`agentRationale`, `thesisForInclusion`) and real scalar
   corrections (share counts, roles) must both be preserved from whichever side actually has them —
   never blanket `--ours`/`--theirs` for these files as a whole file; resolve conflict-block by
   conflict-block.
5. **The actual closeout sequence, once verification (step 1) is complete:**
   1. `git fetch origin`
   2. Confirm the feature branch tip is a real ancestor of `origin/main`:
      `git merge-base --is-ancestor <branch-tip> origin/main`
   3. In the **main checkout**: `git status --porcelain` first — if non-empty, identify whether
      those changes are yours (from this session) or pre-existing/unrelated (another session's
      WIP). Never discard either without explicit confirmation of which is which.
   4. If pre-existing unrelated changes block a fast-forward: `git stash push -u` (only with
      explicit instruction per this file's "No git stash" rule above — ask first), fast-forward,
      `git stash pop`, resolve any conflicts per step 4's rule, commit, `git stash drop` (only the
      specific entry just resolved — never touch other stash entries from unrelated sessions).
   5. If the worktree itself has commits made *after* its PR was opened/merged (should not happen
      if step 2 was followed, but verify): cherry-pick them onto main individually, resolving
      conflicts per step 4's rule, before removing the worktree — never remove a worktree with
      unmerged real content still only living there.
   6. `git worktree remove <path>` (add `--force` only if the failure is a genuinely empty
      leftover directory like a scratch `temp/` folder — check contents first, never force past
      real files).
   7. Delete local (`git branch -d`, or `-D` only after confirming via `git diff <branch> main`
      that main is a strict superset — never delete on faith) and remote
      (`git push origin --delete <branch>`) feature branch.
   8. Confirm clean state: `git worktree list` and `git branch --list`/`git branch -r` show no
      trace of the closed-out branch.
6. **Do not treat "PR merged" as "wave done."** Per CLAUDE.md rule 15, PR merge triggers this
   closeout sequence — it is not the finish line. The wave is done when steps 1-5 above are all
   complete and verified, not when GitHub shows the merge button was clicked.
