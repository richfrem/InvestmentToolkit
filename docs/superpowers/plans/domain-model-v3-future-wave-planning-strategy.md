# Domain Data Model v3 Migration — Future Wave Planning Strategy

## Recommendation

Do **not** fully draft all later wave implementation plans now.

Draft detailed implementation plans **one wave at a time**, after the previous wave exit report has been reviewed and merged.

Reason: each wave changes the repository state, consumer inventory, tests, archive status, and remaining JSON surface. A detailed plan written too early risks becoming stale and repeating the earlier failure mode where assumptions replaced verified code inspection.

## Best Operating Model

For every wave:

1. Finish the current wave.
2. Produce the wave exit report.
3. Review the actual results.
4. Merge/push the wave branch.
5. Clean the worktree.
6. Start a fresh session for the next wave.
7. Re-read the current code and data before writing that wave's detailed implementation plan.
8. Execute the next wave under conditional autonomy.

## What Can Be Drafted Now

It is useful to create **lightweight planning skeletons** for later waves, but not full implementation plans.

Each skeleton should include:

- domain scope
- likely source files
- expected target tables
- known producers
- known consumers
- suspected risks
- required dry-run report
- wave completion bar
- archive criteria
- stop conditions

Do **not** include exact implementation steps until the agent has re-read live code at the start of that wave.

## Why Not Fully Plan All Waves Now?

Later wave plans depend on facts that will change:

- Wave 1 may remove or rewrite projection consumers.
- Wave 2 may change target/watchlist access patterns.
- Wave 3 may change holdings/account assumptions.
- Wave 4 may depend on portfolio/account behavior established in Wave 3.
- Wave 5 may shrink if earlier waves remove consumers or generated-file dependencies.

A detailed plan written too early may encode stale assumptions.

## Recommended Next Planning Sequence

### Current

Wave 1 is executing.

Do not draft final Wave 2 implementation details until Wave 1 exit report is complete and merged.

### After Wave 1

Draft Wave 2 implementation plan based on:

- Wave 1 exit report
- current main branch
- actual `target-portfolio.json` and `watchlist.json`
- stale path findings
- `portfolio_action.py` discovery
- real producer/consumer re-scan

### After Wave 2

Draft Wave 3 implementation plan based on:

- current account/holding data behavior
- broker/private file rules
- real `portfolio.json` shape
- account/cash mapping decisions

### After Wave 3

Draft Wave 4 implementation plan for:

- trade-log.json
- orders_executed.jsonl
- cash_flows.json

### After Wave 4

Draft Wave 5A–5E implementation plans for:

- generated research runtime cutover
- TA sweep events
- daily brief events
- predictions
- account policy

## Universal Wave Template

Each detailed wave plan should include these sections:

### 1. Scope

- domain name
- current files
- target tables/repositories
- explicit non-goals

### 2. Fresh Verification

Before writing code, re-read:

- real source files
- real producer code
- real consumer code
- tests
- skill/agent references
- context-bundler manifests if relevant

### 3. Producer / Consumer Inventory

| File | Role | Current Path | New Path | Test Required | Notes |
|---|---|---|---|---|---|

### 4. Dry-Run Migration

Must report:

- source file count
- source record count
- target row count expected
- shape variants
- parse failures
- anomalies

### 5. Approval / Gate

Proceed to real migration only if:

- counts reconcile
- no unexplained shape variants
- no unresolved parse failures
- rollback path is clear

### 6. Real Migration

Must be:

- idempotent
- reversible
- parity-tested
- documented

### 7. Producer Cutover

All real producers must write SQLite/domain repositories.

### 8. Consumer Cutover

All real consumers must read SQLite/domain repositories.

### 9. Archive

Archive old files only after producer + consumer cutover is proven.

Use:

```bash
git mv old/path ARCHIVE/old/path
```

Never `rm`.

### 10. Validation

Required:

- tests
- grep for old file I/O
- repository-only SQL check
- context-bundler impact
- full relevant validation gate

### 11. KPI Table

| KPI | Before | After | Notes |
|---|---:|---:|---|
| Active JSON/JSONL files | | | |
| Files archived | | | |
| JSON reads removed | | | |
| JSON writes removed | | | |
| Producers migrated | | | |
| Consumers migrated | | | |
| Context bundle files removed | | | |

### 12. Exit Report

The wave exit report must include:

- what changed
- what was archived
- what remains
- validation output
- rollback instructions
- branch/commit IDs
- next-wave recommendations

## Standing Stop Conditions

Stop immediately if:

- source count and target row count do not reconcile
- any new data shape appears without a test
- producer still writes old JSON/JSONL after claimed cutover
- consumer still reads old JSON/JSONL after claimed cutover
- direct SQLite access appears outside approved repositories/services
- generated/static files remain runtime source of truth for migrated domains
- tests fail in a migration-related way
- archive would remove rollback ability
- retained JSON lacks approved rationale

## Bottom Line

Create detailed plans one wave at a time.

Create reusable lightweight skeletons now if helpful.

Do not pre-script later waves in detail before the current repository state is known.
