# Workpackage & Worktree Synchronization Protocol

## Overview
This document defines the **MANDATORY** lifecycle for implementing Work Packages (WPs) in the InvestmentToolkit. It is designed to ensure:
1.  **Isolation:** Work happens in dedicated worktrees.
2.  **Safety:** Remote backups exist before local deletion.
3.  **Sanity:** The `main` branch is always the Single Source of Truth locally.

## The 5-Phase Protocol

![Workflow Diagram](../diagrams/workpackage-worktree-sychronization.mmd)

### 0. Initialization
- **Rule:** The Git Branch Name **MUST** exactly match the Worktree Folder Name suffix.
- **Command:** `spec-kitty implement WP-xx` (or manual `git worktree add`).
- **Critical Action:** `cd .worktrees/WP-xx` immediately.

### Phase 1: The Safety Backup
**Context:** Inside Worktree.
Before even thinking about merging, the work must be secured on GitHub.
- `git add .`
- `git commit -m "feat: implement WP-xx"`
- `git push origin WP-xx`
- **Signal Completion:**
    - `spec-kitty agent tasks move-task WP-xx --to for_review --note "Impl complete"`
- **Decision:** If review fails, go back to Worktree and iterate. If pass, convert to Phase 2.

### Phase 2: The "Single Truth" Merge
**Context:** Root Directory (`main` branch).
We merge locally to verify integration *before* asking for a PR review.
- `cd ../..` (Return to Root)
- `git checkout main`
- `git merge --squash WP-xx` (Into **LOCAL** Main)
- `git commit -m "feat(WP-xx): complete implementation"` (Save to **LOCAL** Main)

### Phase 3: Verification (Smoke Test)
**Context:** Root Directory.
Prove that the merge didn't break the build.
- `npm run dev` (Frontend & Backend)
- **If Fail:** Reset `main`, go back to Worktree, fix, and repeat Phase 1.
- **If Pass:** Proceed to Phase 4.

### Phase 4: The Mandatory Purge
**Context:** Root Directory.
Eliminate "zombie" environments to keep the repo clean.
- `git worktree remove .worktrees/WP-xx --force`
- `git branch -D WP-xx` (Delete LOCAL branch only)
- `git worktree prune`

### Phase 5: Handover & Sync
**Context:** GitHub & Root Directory.
The local repo is clean and updated. The remote feature branch exists.
- **Action:** Developer opens a Pull Request from `origin/WP-xx` to `main`.
- **Merge:** Merge PR via GitHub Interface.
- **Sync:** `git pull origin main` (Updates local `main` with the PR merge commit).
- **Result:** Local `main` is clean, synced, and ready for the NEXT Work Package.

## Violation Consequences
*   **Mismatched Names:** Confusion during cleanup (deleting wrong branch).
*   **Skipping Phase 1:** Data loss if local delete happens before push.
*   **Skipping Phase 3:** Broken `main` branch locally.
