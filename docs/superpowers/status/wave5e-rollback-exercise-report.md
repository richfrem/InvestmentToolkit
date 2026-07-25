# Wave 5E — Rollback Exercise (physically executed)

## Commands and real output

```
$ git worktree add /tmp/wave5e-rollback-exercise 8ceaffc3
Preparing worktree (detached HEAD 8ceaffc3)
HEAD is now at 8ceaffc3 feat: add update_portfolio_policy.py CLI, the new manual-edit write path (Wave 5E Task 5)

$ git revert --no-commit 31f44075 25f639a8
# clean, no conflicts

$ git status --short
M  investment_screener/backend/py_services/rebalancer.py
M  investment_screener/backend/src/services/ThesisService.ts
M  investment_screener/backend/tests/py_services/test_rebalancer.py
M  investment_screener/backend/tests/services/ThesisService.spec.ts

$ git commit -m "revert: Wave 5E Tasks 4a/4b (rollback exercise, throwaway)"
[detached HEAD 31f2e222] revert: Wave 5E Tasks 4a/4b (rollback exercise, throwaway)
 4 files changed, 6 insertions(+), 160 deletions(-)
```

Confirmed both consumers reverted to reading `account_policy.json` directly:

```
$ grep -n "account_policy = json.loads" rebalancer.py
736:    account_policy = json.loads(Path(account_policy_path).read_text())

$ grep -n "private getAccountPolicy" ThesisService.ts
177:    private getAccountPolicy(): AccountPolicy | null {
```

## Pre-wave test suite

```
$ python3 -m pytest tests/py_services/test_rebalancer.py -v
============================== 45 passed in 0.23s ==============================

$ npx mocha -r ts-node/register tests/services/ThesisService.spec.ts
  ThesisService.getLatestAIProjection
    ✔ returns null when the ticker has no projections
    ✔ returns null when projections exist but none are source AI_AGENT
    ✔ returns the latest AI_AGENT projection by version, not the file-order default
    ✔ reads through ProjectionService, not through data/projections/*.json on disk
  ThesisService.getPortfolioItems (Wave 3 Task 6)
    ✔ returns [] when the tmp SQLite db has no priced positions and no portfolio.json fallback data
    ✔ reads per-symbol quantity/price aggregated from account_investment/investment_price, not portfolio.json
  6 passing (26ms)
```

45/45 Python + 6/6 TS passing against the reverted, JSON-only code (test counts are 1 fewer
each than the post-cutover suite, correctly — the new SQLite-proof tests were part of the
reverted commits too).

## Cleanup

```
$ git worktree remove /tmp/wave5e-rollback-exercise --force
$ git worktree list
/Users/richardfremmerlid/Projects/InvestmentToolkit                                          07ad08f1 [main]
/Users/richardfremmerlid/Projects/InvestmentToolkit/.claude/worktrees/wave5e-account-policy  8ceaffc3 [wave5e-account-policy]
```

Throwaway worktree fully removed, `main` untouched, no orphaned entries.

## Note

`account_policy.json` had not yet been archived at the point this exercise ran (Task 7, archival,
is scheduled after this task) — the reverted code reads it directly from its original, still-present
location, no restore-from-`ARCHIVE/` step was needed for this exercise.
