# Rollback Exercise Report (New Priority 3)

The documented rollback procedure (`research-migration-execution-report.md` §5) was **physically
executed**, not just reviewed. Evidence below at every step.

---

## 1. Backup Before Touching Anything

Backed up, outside the repo, before any destructive step:
`investment_screener/backend/data/projections/`, `research/` (216 files), `observations.jsonl`
(MD5 `ad506276...`), `intelligence.sqlite` (MD5 `909d4452...`). `git status` confirmed clean
(only the 2 pre-existing untracked files from the earlier session) before starting, and HEAD was
`e37a5066` (this session's Priority 1/2 fix commit).

## 2. Rollback Executed

1. `git checkout aed7fd12 -- investment_screener/backend/data/projections/` — `aed7fd12` is
   `f860b29e^`, the commit immediately before the research-corpus migration.
2. `mv research/archive/*.md research/` + `rmdir research/archive`.
3. Removed the 144 generated `.summary.md`/`.timeline.md` files (these didn't exist
   pre-migration; the original rollback doc predates this session's Priority 1 fix and didn't
   anticipate them, but a true return to pre-migration state has to remove them too).
4. `rm observations.jsonl intelligence.sqlite`.

## 3. Rollback Verified

- `git diff aed7fd12 -- .../projections/` → **0 lines** — projections are byte-identical to the
  pre-migration commit.
- `research/` → exactly **152** files (72 canonical + 80 dated), 0 `.summary.md`/`.timeline.md`,
  no `archive/` directory.
- `observations.jsonl` and `intelligence.sqlite` both confirmed absent.
- `AAPL.json`'s pointer confirmed back to `AAPL_2026-05-02.md` (dated shape).
- **The old disk-fallback path was confirmed to actually work**, not just structurally present:
  read `research/AAPL_2026-05-02.md` directly — succeeded, 3842 bytes.
- **Graceful degradation confirmed at the real route layer**: called
  `queryLatestResearchFromLedger('AAPL_2026-05-02.md')` against the compiled route code with no
  `intelligence.sqlite` present — returned `null` (logged a warning, did not throw), exactly as
  `docs.ts`'s try/catch is written to handle, and the disk fallback branch is what a live request
  would have hit next.

**Rollback: PASSED with real evidence**, not just as a documentation review.

## 4. Forward Migration Re-Run (Restore Current Good State)

Re-ran the full pipeline for real, in order: `migrate_research_to_ledger.py` (80 migrated) →
`rebuild_db.run_rebuild()` (80/80 verified) → `migrate_research_report_pointers.py` (**119**
rewritten this time, not 118 — the fix from Priority 1/2, `DATED_RE` matching against
`Path(report).name`, now catches OKLO's full-path pointer on the very first pass instead of
needing a separate manual correction) → `render_all_ticker_views.render_all_views()` (72
tickers, 144 files).

## 5. Restored State Verified Against Pre-Rollback Backup

- `intelligence.sqlite`: 80/80 events in both; compared by `(ticker, effective_at) →
  body_markdown` (not raw `event_id`, which is expected to differ between independent migration
  runs) — **0 content differences**.
- `observations.jsonl`: 80/80 lines in both; same key-based comparison — **0 content
  differences**.
- `projections/`: `diff -rq` against the pre-rollback backup — **0 files differ**.
- `research/*.summary.md` / `*.timeline.md`: 144/144 files present; content compared with the
  `generatedAt` timestamp line normalized out — **0 real content differences**. (The raw files
  did differ by that one cosmetic timestamp line, since `view_generator` stamps render time;
  reverted via `git checkout --` after verification so the working tree matches the committed
  `e37a5066` state exactly.)
- Full intelligence/migration test suite re-run post-restore: **31/31 passed**.
- `git status` after cleanup: clean except the 2 pre-existing untracked files
  (`observations.jsonl`, `package-lock.json`) that predate this entire exercise.

## Summary

| Question | Answer |
|---|---|
| Was rollback physically executed? | **Yes** |
| Does rollback correctly restore pre-migration state? | **Yes** — byte-identical projections, exact pre-migration file set, ledger/DB removed |
| Does the old (pre-migration) disk-fallback path actually work post-rollback? | **Yes** — verified by direct read and by exercising the real route function with the DB absent |
| Does re-running the forward migration restore the current good state? | **Yes** — verified content-identical (not just row-count-identical) against the pre-rollback backup at every layer: DB, JSONL, projections, generated views |
| Any data loss or corruption during the exercise? | **No** |
