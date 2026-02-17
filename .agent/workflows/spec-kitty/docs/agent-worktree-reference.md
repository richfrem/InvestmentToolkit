# Agent Worktree Quick Reference

> **⚠️ CRITICAL**: This document is a cheat sheet for AI agents. Read before ANY git operations.

## The Golden Rule

```
IF you are implementing a WP:
    ALL file operations happen in .worktrees/###-feature-WP##/
    NEVER edit files in the main repository root
```

---

## 1. Naming Conventions

### Worktree Directory Names
```
.worktrees/<feature-number>-<feature-slug>-<WP-ID>/
```

**Examples:**
- `.worktrees/0002-screener-ui-improvements-WP07/`
- `.worktrees/0001-auth-system-WP03/`
- `.worktrees/0014-dashboard-redesign-WP01/`

### Branch Names
Branches should match the worktree pattern:
```
<feature-number>-<feature-slug>-<WP-ID>
```

**Examples:**
- `002-screener-ui-improvements-WP07`
- `001-auth-system-WP03`

### ⚠️ WARNING: Inconsistent Naming
Sometimes worktrees get created with non-standard names like:
- `WP03-analyst-forecast` (missing feature number)
- `feature/wp06-valuation-polish` (wrong format)

**If you see inconsistent naming:** Don't panic. Use whatever exists, but note it for cleanup later.

---

## 2. Where Am I? (Location Check)

**Before ANY git operation, run:**
```bash
pwd && git branch --show-current
```

### Expected Output When in a Worktree:
```
/path/to/project/.worktrees/0002-feature-WP07
002-feature-WP07
```

### Expected Output When in Main Repo:
```
/path/to/project
main
```

### 🚨 DANGER Signs:
| You are at | Branch shows | ⚠️ Action Required |
|------------|--------------|-------------------|
| Main repo root | `main` | ✅ OK if running accept/merge |
| Main repo root | `main` | ❌ STOP if trying to implement |
| Worktree | `main` | ❌ Something is wrong, fix it |
| Worktree | WP branch | ✅ OK for implementation |

---

## 3. Commit From the Worktree Only

### ✅ CORRECT: Commit from Worktree
```bash
cd /path/to/.worktrees/0002-feature-WP07/
git add .
git commit -m "feat(WP07): implement feature"
```

### ❌ WRONG: Commit from Main Repo
```bash
cd /path/to/InvestmentToolkit/  # Main repo - WRONG!
git add .
git commit -m "feat(WP07): implement feature"  # Commits to MAIN!
```

---

## 4. Push to Feature Branch, NEVER to Main

### ✅ CORRECT: Push Feature Branch
```bash
# From worktree
git push origin 002-screener-ui-improvements-WP07
```

### ❌ WRONG: Push to Main
```bash
git push origin main  # NEVER DO THIS
```

**Why?**
- Main branch has protection
- Requires PR to merge
- Direct push will fail or corrupt history

---

## 5. The Full WP Implementation Flow

```bash
# 1. Start WP (creates worktree)
spec-kitty implement WP07

# 2. IMMEDIATELY change directory
cd .worktrees/0002-screener-ui-improvements-WP07/

# 3. Verify location
pwd && git branch --show-current

# 4. Do all work HERE
# ... edit files, run tests ...

# 5. Commit (still in worktree)
git add .
git commit -m "feat(WP07): description"

# 6. Backup to origin (feature branch)
git push origin 002-screener-ui-improvements-WP07

# 7. Move to review (Use the CLI)
python3 .kittify/scripts/tasks/tasks_cli.py update <FEATURE> <WP07> for_review \
  --agent "<AGENT-NAME>" --note "Implementation complete"

# 8. Deterministic Closure Protocol (The Finish Line)
# Chain: Review -> Accept -> Retro -> Merge -> Verify -> Intel

# A. Review (WP -> Done)
spec-kitty agent workflow review --task-id WP07

# B. Accept (Feature)
cd <PROJECT_ROOT>
spec-kitty accept --mode local --feature <SLUG>

# C. Retrospective (MANDATORY)
/spec-kitty_retrospective

# D. Merge (from ROOT)
spec-kitty merge --feature <SLUG>

# E. Verify & Intel Sync
git worktree list
python3 plugins/rlm-factory/scripts/distill.py --path kitty-specs/<SLUG>/
```

---

## 6. Common Agent Mistakes

| Mistake | Why It's Bad | How to Avoid |
|---------|-------------|--------------|
| Editing files in main repo while WP is active | Changes go to wrong branch | Always `cd .worktrees/XXX` first |
| Committing doc updates to main | Diverges local main from origin | Let `move-task` handle status files |
| Pushing to origin/main | Branch protection blocks it | Push feature branch only |
| Using relative paths | Lose track of which repo | Use ABSOLUTE paths always |
| Forgetting to `cd` after implement | Work happens in wrong location | Verify `pwd` after every implement |
| Skipping Retrospective | Merge fails or process violation | Always run `/spec-kitty_retrospective` before merge |
| Merging from Worktree | `@require_main_repo` error | Always `cd <PROJECT_ROOT>` before merge |

---

## 7. Absolute Path Cheat Sheet

When using file tools, always use absolute paths:

| Operation | Path Format |
|-----------|-------------|
| View file in worktree | `/full/path/.worktrees/0002-feature-WP07/src/file.ts` |
| Edit file in worktree | `/full/path/.worktrees/0002-feature-WP07/src/file.ts` |
| View file in main | `/full/path/InvestmentToolkit/src/file.ts` |

**Template:**
```
<project_root>/.worktrees/<feature-num>-<feature-slug>-<WP-ID>/<relative_path>
```
