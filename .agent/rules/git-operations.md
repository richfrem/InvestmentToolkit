---
description: Rules for safe git operations — what requires explicit approval, what is forbidden, and how to handle push & lockfile conflicts.
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

### 1. No git stash without explicit instruction
Never run `git stash`, `git stash pop`, or `git stash apply` unless the user explicitly says to.
**Reason:** Stashing risks applying stale edits onto new branches and causing silent regressions.

### 2. Lockfile Conflict Protocol (`skills-lock.json`)
`skills-lock.json` contains machine-generated timestamps. When a branch or PR has conflicts in `skills-lock.json`:
- **NEVER** edit conflict markers by hand (`<<<<<<<`, `=======`, `>>>>>>>`).
- **NEVER** leave a PR in conflict state after pushing.
- **ALWAYS** resolve immediately via:
  ```bash
  git checkout --ours skills-lock.json
  python3 plugins/plugin-manager/scripts/plugin_add.py plugins/ -y
  git add skills-lock.json
  ```

### 3. Pre-Push Freshness Verification
Before pushing a feature branch for PR merge:
1. Verify the branch is up to date with `origin/main`:
   ```bash
   git fetch origin main
   git merge origin/main
   ```
2. If `skills-lock.json` conflicts, apply Rule 2 immediately before pushing.
3. Verify working directory is clean (`git status`) and push with `-u origin <branch>`.

### 4. When a push is rejected
If `git push` is rejected because the remote is ahead:
1. Run `git fetch origin` and `git merge origin/<branch>` or `git pull --rebase` (no stash).
2. If conflicts occur in `skills-lock.json`, resolve via Rule 2.
3. Push once clean. Never force-push around a rejected push.

### 5. No force push to main/master
Never `git push --force` to main or master under any circumstances.

### 6. No --no-verify
Never skip hooks with `--no-verify` unless the user explicitly requests it.

### 7. Commit only what is asked & required
- Commit only files within the task scope.
- Auto-modified files like `.DS_Store` or `uv.lock` should not be committed unless relevant.
- When `skills-lock.json` or `symlinks.json` changes as a direct result of adding/modifying skills or plugins, commit them together with the changes.

### 8. Mandatory Pre-Branch Fetch & Pull Gate
Before executing `git worktree add` or `git checkout -b` for ANY feature or chore:
1. Switch to `main`: `git checkout main`
2. Fetch and pull latest remote: `git fetch origin main && git pull origin main`
3. Verify local matches remote: `git rev-parse HEAD` equals `git rev-parse origin/main`.
Branching from an un-pulled local state is strictly prohibited.

### 9. Strict Working-Directory Confinement
All commands, tool executions, and file edits MUST remain strictly within the current repository tree (`InvestmentToolkit`). Never pass `-C ../<dir>`, never reference files outside the workspace root, and never inspect or touch parallel repositories (such as `agent-plugins-skills`) unless explicitly reviewed, approved, or authorized by the user.

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
- Fetching and merging `origin/main` into the current working feature branch to keep PRs conflict-free
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
