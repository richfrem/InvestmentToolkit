# Implementation prompt: SQLite as the single source of truth

Paste everything below the line into a new Claude Code session started in `/Users/richardfremmerlid/Projects/InvestmentToolkit` (the main checkout, on `main`).

---

You are implementing an approved plan in the InvestmentToolkit repo. Work one workstream at a time and finish it before starting the next.

## Read first, in this order
1. `AGENTS.md` (all of it; follow it exactly).
2. `docs/plans/sqlite-single-source-of-truth-plan.md` (why, findings, workstreams, decisions).
3. `docs/plans/sqlite-single-source-of-truth-spec.md` (exact requirements, schema, per-tool behavior, acceptance criteria).
4. `.agent/rules/coding-conventions.md` and `.agent/rules/git-operations.md`.

## The goal
Portfolio data (holdings, targets, thesis state, trades, cash, price levels, alerts, valuations, thesis breakers) lives only in `domain_model.sqlite`. Research and analysis live only in the ledger `intelligence.sqlite`; JSON/JSONL/markdown copies are generated exports. No JSON file, no JSON fallback. Several tools still read or write `portfolio.json` / `target-portfolio.json`, which no longer exist, so they fail or silently do nothing (`update_thesis.py`, `validate_weights.py --mode target`, `update_price_levels.py`, `generate_review.py`, `harvest_predictions.py`, `lock_and_normalize_targets.py`, the `place_order.py` freshness gate, `system_health.py`, the Express routes' file fallbacks, the UI position editor, `tradingview-cdp/cli.js alert list --filter`). The plan lists all of them with evidence.

## Decisions already made
- Portfolio data SQLite only (decided by the owner). Research goes into the ledger; files are exports (decided by the owner).
- Defaults, in force unless the owner says otherwise at the start of the session: add `thesis_breaker` and `thesis_breaker_state` tables (D3); the role vocabulary is the SQLite statuses `accumulate/trim/exit/initiate/watchlist` (D4); remove the UI manual position editor (D5). Ask the owner once, in your first message, to confirm or override D3-D5, then proceed on the defaults if they do not answer.
- Moving or deleting any data file needs the owner's explicit OK for that specific file (D6). Nothing is deleted; retirement means moving to `ARCHIVE/`.

## How to work
- **Order:** WS0 (guard and governance) first, then WS1, WS2, WS3, WS4, WS5, WS6, WS7 as in the plan. WS5 (research) may run any time after WS0. Finish a workstream completely (tests, verification, PR) before starting another. Do not start side tasks.
- **Worktree first, always.** Create a new worktree off a freshly fetched `origin/main` for each workstream: `git fetch origin && git worktree add -b <branch> .claude/worktrees/<name> origin/main`. Never edit code in the main checkout. Link the CDP modules into each worktree you test in: `ln -s /Users/richardfremmerlid/Projects/InvestmentToolkit/tradingview-cdp/node_modules tradingview-cdp/node_modules` (remove the symlink before removing the worktree).
- **Test first.** For each behavior: write a failing test, watch it fail for the right reason, then make it pass. Use real temporary SQLite databases (`initialize_db(tmp_path)`); do not mock the repositories. Run tests in the worktree, never the main checkout.
- **Reuse, do not duplicate** (AGENTS.md rule 22). Existing loaders: `portfolio_io.load_portfolio_state / load_target_weights / load_thesis_holdings`, `portfolio_repository.get_last_synced_at`, `investment_repository`, `investment_price_repository`, `update_targets.py`, `set_standing_decision.py`. For research use the existing `migrate_*_to_ledger.py`, `persist_research.py`, `query_ledger_*`.
- **Comments:** describe current behavior only. No "previously", "Wave N cutover" or "retired" narration. Follow the file-header convention (Purpose, Layer, Usage, Key Functions index, Key Input/Output Dependencies).
- **Commits and PRs:** one PR per workstream, feature branch pushed to origin (permitted), PR opened with a summary, test evidence and caveats. Commit messages end with the `Co-Authored-By` trailer given in your session's attribution reminder; PR bodies end with the "Generated with Claude Code" line. Commits under `plugins/` need a staged evolution-log entry in `plugins/portfolio-advisor/references/evolution-log.md` (append away from the last line to avoid merge conflicts with other open PRs). **Do not merge** a PR unless the owner tells you to; after the owner merges, do the post-merge cleanup (fetch, verify the tip is an ancestor of `main`, remove the worktree, delete the local and remote branch).
- **Data safety:** back up before any database write (`db_backup.py`). Migrations and loaders are dry-run by default and need an approved report before `--write`. Verify real-data effects in the **main checkout's** databases, not a worktree copy (AGENTS.md pitfall 29). Never overwrite gitignored data files.
- **Subagents:** only if needed, and only Sonnet or Haiku, never Opus.
- **Do not touch** the owner's uncommitted edits in the main checkout (`.agent/rules/git-operations.md`, `.env.example`).
- The work-intake control plane is disabled in this repo (`.agents/skills/work-intake` does not exist), so skip the intake gate.

## First task: WS0
1. Confirm D3-D5 (one short message), then create the WS0 worktree.
2. Copy `/Users/richardfremmerlid/Projects/InvestmentToolkit/temp/evaluations/audit_sqlite_usage.py` (gitignored scratch in the main checkout) into the repo as specified in spec §4, with its `--self-test` as a pytest module. Run it and compare with Appendix A of the spec; if the numbers differ, trust the code and say so.
3. Add the guard test (red on purpose), wire it into `run_tests.py`, rewrite `allowed-json-register` and the `audit_json_usage.py` classification, write ADR-038.
4. Verify, open the PR, report.

## What to report
After each workstream, reply with: what changed (files and behavior), test evidence (commands and counts), what you did not verify, and the PR link. Keep it short. State failures plainly with output. Never say "done" or "fixed" without a command's output that shows it.

## Stop and ask only if
A requirement here contradicts the code you find, a change would touch data the owner has not approved, or a decision outside D3-D6 is needed. Otherwise proceed.
