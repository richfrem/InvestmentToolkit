# Wave 1 (Projections) — Handoff

Status: **Complete, PR open, awaiting review/merge. Wave 2 not started.**

## What Wave 1 Accomplished

Migrated `investment_screener/backend/data/projections/*.json` — the real corpus turned out to
be **82 files**, not the 144 originally assumed in planning — into the v3.2 SQLite domain model
(`projection_version`/`projection_scenario` tables, built in Wave 0). Both real producers
(`ProjectionService.ts`/new `ProjectionRepository.ts`, `apply_catalyst.py`) and all 18 real
consumers were cut over to read/write SQLite exclusively. The source JSON directory was archived
via `git mv` after every gate (parity, cutover, grep verification, tests) passed.

**JSON reduction:** 82 → 0 active files for this domain. First wave to actually move the JSON
count, per this whole migration's non-negotiable goal (Wave 0 was schema-only, correctly reported
all-zero KPIs).

**Files archived:** 82, at `ARCHIVE/investment_screener/backend/data/projections/`, full git
history preserved via `git mv` (100% rename detection).

## Six Real Bugs Found and Fixed (not scope creep — each blocked correctness)

1. `ProjectionService.saveProjection`'s upsert-by-id-then-version-increment semantics — required exact preservation, not simplification.
2. **Real production schema mutation via an eager singleton** — `ProjectionRepository`'s constructor was silently `ALTER TABLE`-ing the real `domain_model.sqlite` just from module import. Fixed: schema ownership moved fully into Python's `db_client.py`, runtime `ALTER TABLE` removed from TS.
3. `getProjections`/`getAllProjections` returning full version history instead of current-state-per-identity — a real spec-breaking regression caught before any consumer built on it.
4. **11/82 real tickers where naive `MAX(version)` would return the wrong, stale entry** — concretely, ticker `BW`: naive logic picks a stale BUY $27.13 when the real latest signal is SELL $8.83. A genuine trading-signal-inversion risk, fixed with `get_latest_projection_by_source()`.
5. `CREATE TABLE IF NOT EXISTS` is a no-op against an already-existing file, so new columns never reached the real database — `apply_catalyst.py` would have crashed with a raw `sqlite3.OperationalError` against 100% of real data. Fixed with a general schema self-heal + real backfill.
6. `peer_bench.py`'s stale CLI flag silently passed unused arguments after a sibling task's rewire, returning empty metrics for every call.

Every one of these was caught by an independent reviewer subagent verifying claims against real
data/code (not by the implementer's own say-so), following this migration's standing discipline —
this repository's history includes a prior effort that overclaimed completion, so every report in
this wave was treated as an unverified claim until checked.

## Wave KPI Summary

| KPI | Value |
|---|---|
| Active JSON files before | 82 |
| Active JSON files after | 0 |
| Files archived | 82 |
| Producers migrated | 2 / 2 |
| Consumers migrated | 18 / 18 |
| Real bugs found & fixed | 6 |
| Migration parity | 82/82 tickers matched exactly (full check) |
| Test regressions introduced | 0 |

Full KPI table, validation evidence, and per-file producer/consumer status:
`docs/superpowers/status/wave1-projections-report.md`

## Open Issues (non-blocking, named for whoever picks these up)

- **Doc/eval-fixture text** still references `data/projections/...` descriptively (plugin.json
  `canonical_path`, several `evals.json`, SKILL.md prose) — not runtime code, not fixed this wave.
  Candidate for a documentation-sync pass, possibly folded into a future wave's plugin/skill
  reference update step.
- **`persist_etf_analysis.py`'s dual-write** to `data/etf_analysis/{TICKER}.json` has no
  rollback/consistency guarantee against its new SQLite sync — pre-existing risk shape, not new
  debt, but worth a tracked follow-up.
- **An unrelated `git stash pop` conflict** on 4 files outside Wave 1's scope
  (`fetch_portfolio_heatmap.py`, `portfolio.ts`, `BrokerSyncService.ts`, `broker_data.js`) was
  found and safely resolved mid-wave (restored to `HEAD`, verified lossless, the source stash
  entry — `stash@{0}`, someone's unrelated WIP on `main` — left fully intact). Worth a reminder
  that bare `git stash`/`git stash pop` must never be used in a worktree per this repo's
  CLAUDE.md, since the stash stack is shared across all worktrees.

## Remaining Migration Waves (from the approved implementation plan)

- **Wave 2** — Investment/target/watchlist/price-levels/notes/alerts/thesis-breaker-state
  (`target-portfolio.json`, `watchlist.json`, embedded sub-domains). **Not started.**
- **Wave 3** — Account holdings (`portfolio.json`, gitignored, largest domain — 20 producers,
  ~32 consumers). Not started.
- **Wave 4** — Portfolio operations (trade log, order executions, cash flows). Not started.
- **Wave 5A–5E** — Generated research views (closes prior-effort debt) → TA sweep → daily briefs
  → predictions → account policy. Not started.

## Exact Branch/Commit References

- Branch: `worktree-domain-model-v3-wave1`
- Commit range: `8f41d00f..52d1a6be` (16 commits: 14 implementation + 1 exit report + this handoff not yet committed)
- Base (Wave 0 merge point): `8f41d00f`
- Archive commit: `730daddb`
- Exit report commit: `52d1a6be`
- PR: **#85**, `worktree-domain-model-v3-wave1` → `main`, **open, not yet merged**
- Remote verified: local and `origin/worktree-domain-model-v3-wave1` HEAD both `52d1a6be` (byte-identical)
- **`main` has NOT been updated** — Wave 0's work is on `main` (merged via PR #84), but Wave 1's commits exist only on this branch pending PR #85's review/merge.

## Instructions for the Next Fresh Session

1. **If picking up Wave 1 review/merge**: review PR #85 on GitHub, then either merge it yourself or tell the agent to merge once approved. Do not assume it's merged — check `git log origin/main` for commit `730daddb` or `52d1a6be` before trusting anything downstream depends on Wave 1 being on `main`.
2. **If starting Wave 2**: it is gated behind Wave 1's review, per standing instruction. Confirm PR #85 is merged into `main` first. Then follow the same process this wave used: `superpowers:writing-plans` to write Wave 2's detailed task plan (re-reading the real current `target-portfolio.json`/`watchlist.json` code fresh — do not trust the original Wave 1-5E plan's one-line descriptions, per this whole migration's established discipline), then `superpowers:subagent-driven-development` to execute it in a fresh worktree (`EnterWorktree`, fast-forward from `main` if needed).
3. **Wave-level autonomy applies going forward** (per user instruction mid-Wave-1): execute each wave end-to-end without per-task pause, fix issues found along the way, only stop for evidence-based hard-stop conditions (parity mismatch, unexplained row-count delta, new data shape without a test, a producer/consumer still on the old JSON path, a repository-layer bypass, new test failures, archive-readiness grep still finding real I/O, an archive step that would remove rollback capability, a permanent hybrid state). Produce a wave exit report + this kind of handoff doc at the end of every wave, then stop for review before the next wave.
4. **Real data caveat**: `investment_screener/backend/data/domain_model.sqlite` now holds real production data (82 investments, 115 `projection_version` rows, 345 `projection_scenario` rows, `source` backfilled for all 115). It is gitignored — do not assume a fresh checkout has it; `initialize_db()` + a migration re-run reconstructs it if needed, per the rollback instructions in the exit report.
