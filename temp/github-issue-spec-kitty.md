# [Feature Request] Improve AI Agent Compatibility with Worktree Workflow

### Summary

After extensive testing with multiple AI agents (Gemini/Antigravity, Claude), we've identified several pain points in the worktree workflow that consistently cause agents to make errors. This issue documents these struggles and suggests improvements.

### Context

We're using spec-kitty v0.13.21 with the workspace-per-WP model (0.11.0+) in a project with multiple agents working on features.

### Pain Points Observed

#### 1. `move-task` Commits to Main Branch
**Problem:** When running `spec-kitty agent tasks move-task WP## --to for_review` from a worktree, the command commits status changes to the **main branch** in the main repository.

**Impact:** This causes local `main` to diverge from `origin/main`, leading to complex rebase conflicts later.

**Observed Behavior:**
```
# Running from .worktrees/002-feature-WP07/
$ spec-kitty agent tasks move-task WP07 --to for_review

Note: Using main repo's kitty-specs/ (worktree copy ignored)
→ Committed status change to main branch  # <-- This is the problem
```

**Suggestion:** Either:
- Don't commit status changes automatically (let agents commit explicitly)
- Commit to the worktree's branch instead
- Add a `--no-commit` flag

#### 2. Missing Worktrees Block `spec-kitty merge`
**Problem:** If earlier WPs (WP01-WP05) were completed before the worktree-per-WP model was adopted, `spec-kitty merge` fails because it expects worktrees for ALL WPs.

**Error:**
```
Pre-flight Check
┃ WP01 ┃ ✗ ┃ Missing worktree for WP01. Expected at...
┃ WP02 ┃ ✗ ┃ Missing worktree for WP02. Expected at...
```

**Suggestion:** 
- Add a `--skip-missing-worktrees` flag
- Or detect if WP work is already merged into main and skip those WPs

#### 3. `spec-kitty accept` Auto-Detection Issues
**Problem:** When multiple features exist, `spec-kitty accept` sometimes auto-selects the wrong feature.

**Observed:**
```
$ spec-kitty accept
ℹ️  Auto-selected latest incomplete: 001-investment-screener-spec  # Wrong!
# Should have selected 002-screener-ui-improvements
```

**Suggestion:** Add clearer prompts or require explicit `--feature` flag in multi-feature repos.

#### 4. Branch/Worktree Naming Inconsistencies
**Problem:** Agents get confused when worktrees/branches use different naming patterns:

- Standard: `.worktrees/002-screener-ui-improvements-WP07/` → `002-screener-ui-improvements-WP07`
- Legacy: `.worktrees/WP03-analyst-forecast/` → `WP03-analyst-forecast` (missing feature prefix)

**Suggestion:** 
- Enforce strict naming convention in `spec-kitty implement`
- Add a `spec-kitty worktree list` command that shows worktree-to-branch mappings clearly

#### 5. No Branch Protection Awareness
**Problem:** Agents try to `git push origin main` after local merge, but main has branch protection. No guidance in CLI output.

**Suggestion:** 
- Detect branch protection and suggest creating a feature branch for PR
- Add `--create-pr-branch` flag to `spec-kitty merge`

### Suggested Documentation Improvements

We've created supplementary documentation to help agents:

1. **Agent Worktree Quick Reference** - Cheat sheet with naming conventions, location checks, common mistakes
2. **Branch Protection Workflow** - Steps for protected main branches
3. **Manual Merge Fallback** - When `spec-kitty merge` can't be used

Would be happy to contribute these docs to the spec-kitty repo if helpful.

### Environment

- spec-kitty version: 0.13.21
- OS: macOS
- Agents tested: Gemini (Antigravity), Claude
- Workflow: Workspace-per-WP (0.11.0+)

### Reproduction Steps

1. Create feature with multiple WPs
2. Complete WP01-WP05 without worktree-per-WP model
3. Complete WP06-WP07 with worktree-per-WP model
4. Try to run `spec-kitty merge` → fails on missing WP01-WP05 worktrees
