# Git Worktree & Branch Lifecycle Protocol

## Context
This project utilizes a Spec-Work-Package (WP) workflow. To prevent "Double Vision" (editing redundant files), path confusion, and uncommitted work loss, the agent MUST follow this lifecycle strictly.

## Phase 1: The Safety Backup
Before any local cleanup, the current state must be preserved on GitHub.
- **Requirement:** The Branch Name MUST match the Worktree Folder Name exactly.
- **Action:** Stage and commit all changes inside the active worktree directory.
- **Push:** Push the branch to origin.
- **Command:** `git add . && git commit -m "backup: WP[XX] [description]" && git push origin [branch_name]`

## Phase 2: The "Single Truth" Merge
Once backed up, the work must be integrated into the stable Root.
- **Action:** `cd` to the project ROOT directory. Verify with `pwd`.
- **Checkout:** `git checkout main`
- **Merge:** `git merge [branch_name] --squash` (Squash is mandatory).
- **Final Main Commit:** `git commit -m "feat: complete WP[XX]"`

## Phase 3: Verification (Smoke Test)
- **Requirement:** The agent MUST run `npm run dev` (or equivalent) from the ROOT directory.
- **Goal:** Confirm features/fixes render from the `main` branch code. 
- **Critical:** Do NOT proceed to Phase 4 if the app fails in the Root.

## Phase 4: The Mandatory Purge (Cleanup)
This is the most critical phase to prevent repo "haunting."
- **Constraint:** No more than ONE worktree (plus the root) may exist at any time.
- **Commands:**
  1. `git worktree remove --force [path_to_worktree]`
  2. `git branch -D [branch_name]`
  3. `git worktree prune`
  4. `git branch` (Verify only `main` remains).
