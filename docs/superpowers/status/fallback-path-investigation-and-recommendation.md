# Fallback Path Investigation & Recommendation (New Priority 1 + 2)

Investigation only — no code changed yet. Every claim below was verified against the live
repository (regex tests, direct DB queries, git history), not inferred from prior reports.

---

## 1. Root Cause (Priority 1 — broken fallback path)

**This is an active, live bug, not a dormant/masked one.** The prior
`post-migration-validation-report.md` concluded "current real-world impact: none, currently
masked" — that conclusion was wrong because it tested `queryLatestResearchFromLedger('AAPL_2026-05-02.md')`
directly with the *old* dated filename. That is not what the frontend actually sends. The real
request path is:

```
DeepDiveModal.tsx  →  fetch(`/api/research/${projection.aiThesis.researchReport}`)
```

`researchReport` was rewritten by the migration to `{TICKER}.summary.md` (confirmed: 118 rewrites,
73 unique tickers). Tracing that exact value through `docs.ts` (`GET /research/:filename`):

1. `DATED_FILENAME_RE.test("AAPL.summary.md")` → **`false`**. The ledger-query branch is gated on
   this regex, so `.summary.md`-shaped filenames **never reach the ledger at all** — confirmed by
   direct regex test.
2. It falls straight to the disk read: `data/research/AAPL.summary.md`. Confirmed via direct
   filesystem read: `ENOENT` — no `.summary.md`/`.timeline.md` file has ever been generated
   anywhere in this repo. `view_generator.py` (built in PR #77) has never been run in production.
3. Result: **404 for all 71 of 73 tickers** whose pointer is ledger-covered (the other 2 —
   PANW, SKHY — were already broken before this migration; see §3).

Separately, and independently: even the 72 real, pre-existing bare `{TICKER}.md` canonical files
that *do* exist on disk would be **rejected with 400** if ever requested directly —
`CANONICAL_FILENAME_RE` only matches `.summary.md`/`.timeline.md`, not bare `{TICKER}.md`.

Also confirmed: `query_ledger_research.py --get` itself only accepts the exact
`TICKER_YYYY-MM-DD.md` shape with an exact date match — it has no "latest for ticker" query mode.
So even if `docs.ts`'s gate were loosened, the ledger query as written could not resolve a
`.summary.md`-shaped request either.

**Bottom line:** the pointer-rewrite script (`migrate_research_report_pointers.py`) and the
ledger-query path (`docs.ts` + `query_ledger_research.py`) were each built and unit-tested in
isolation and were never validated end-to-end together. The rewrite moves pointers to a shape
the query layer doesn't handle, pointing at files nothing has ever generated.

## 2. Evaluating the three options

**Ticker-level evidence gathered before choosing:**
- 73 unique tickers hold a `.summary.md` pointer.
- 71 of those are covered by the ledger (RESEARCH_IMPORT events exist).
- 71 of those 73 **also** have an unrelated bare `{TICKER}.md` file on disk — a leftover from an
  earlier, separate `consolidate_research.py` pass, confirmed to be **different content** than
  what was migrated into the ledger.
- The `view_generator.py` module's own docstring and CLI already document the intended
  workflow: `plugins/stock-valuation/skills/stock-research/SKILL.md` and `stock_valuation/SKILL.md`
  both already call `python3 -m intelligence.event_store ... && python3 -m intelligence.view_generator {TICKER}`
  as the standard two-step for *future* research imports. That wiring is real and already in
  place — confirmed by reading both SKILL.md files.

**(a) Generate real `.summary.md` files via `view_generator.py`** — recommended.
- Matches the architecture the codebase already declares as intended (SKILL.md call sites do
  exactly this for every future research import). The gap is purely a one-time backfill: the
  historical migration only did the ledger-append half, never the render half, for the 72
  backfilled tickers.
- Requires zero changes to `docs.ts` or the pointer-rewrite script — both are already correct
  for this shape.
- Closes 71 of 73 broken pointers immediately and correctly (content sourced from the same
  ledger data already verified byte-parity-correct in the rebuild validation).

**(b) Rewrite pointers to bare `{TICKER}.md`** — rejected.
- Would silently serve **wrong content** for 71 of 73 tickers, since the bare files hold
  different, unrelated text from an earlier consolidation pass, not the migrated research. A
  silent wrong-answer is worse than the current 404 — it would look like it worked.
- Would still 400 today regardless, since `CANONICAL_FILENAME_RE` doesn't match bare `.md`.

**(c) Support both filename patterns in `docs.ts`** — rejected as a primary fix.
- Widening the regex alone fixes nothing; the missing piece is the file content, not filename
  recognition. No pointer in the corpus currently uses the bare-`.md` shape, so there is nothing
  for a widened regex to match today.

## 3. Pointer anomalies (Priority 2)

- **OKLO full path** (`investment_screener/backend/data/research/OKLO_2026-05-02.md`) — **real
  migration-script bug**. `migrate_research_report_pointers.py`'s `DATED_RE` is fully anchored
  (`^([A-Z0-9.\-]+)_\d{4}-\d{2}-\d{2}\.md$`) and requires a bare filename with no `/`, so it
  silently skipped this full-path value. The underlying file *was* correctly migrated (moved to
  `research/archive/OKLO_2026-05-02.md`, event in the ledger) — only the pointer text is stale.
  Fix: rewrite the pointer to `OKLO.summary.md`, matching OKLO's own version-2 entry, which
  already uses that correct shape.
- **`INTC_DEBUG.md`** — **pre-existing legacy anomaly, unrelated to this migration.** Confirmed
  via `git show f860b29e^:...INTC.json` (the commit immediately before the migration) that this
  exact value already existed pre-migration. Content (`"model": "debug-model"`,
  `"rationale": "Testing save with new fields"`) is leftover manual test data from exercising the
  projection-save feature, not a real research report. No file named `INTC_DEBUG.md` has ever
  existed in this repo. Not caused by, and not fixable by, the migration tooling.
- **PANW / SKHY** — **pre-existing legacy anomaly, unrelated to this migration.** Confirmed via
  `git show f860b29e^:...` that both already pointed to dated filenames
  (`PANW_2026-05-02.md`, `SKHY_2026-07-13.md`) *before* migration, and confirmed via full git
  history search that neither file has ever existed anywhere in this repo (not in `research/`,
  not in `archive/`, no matching `RESEARCH_IMPORT` event in `observations.jsonl`). These were
  orphaned pointers already broken before any SQLite work began — the migration's rewrite
  behaved correctly (it can't produce a file that was never there to migrate).

## 4. Recommendation

1. **Priority 1 fix:** backfill `.summary.md`/`.timeline.md` for all 72 ledger-covered tickers by
   running `view_generator.render_ticker_views()` once per ticker (bulk wrapper, TDD, new
   script — no existing bulk entry point found). This requires adding one read-only query
   function to `event_repository.py` (list distinct tickers with ACTIVE `RESEARCH_IMPORT`
   events), per ADR-028's rule that only that module may query `intelligence_event`.
2. **Priority 2 fix (OKLO):** correct the one stale pointer via the existing
   `migrate_research_report_pointers.py` machinery (or a one-line targeted JSON fix), covered by
   a new test case for the full-path shape it currently misses.
3. **Priority 2 (INTC_DEBUG, PANW, SKHY):** flagged, not fixed as part of this pass — these are
   pre-existing data-quality debt unrelated to the SQLite migration, and "fixing" them means
   either removing a debug projection version or accepting there is no real research content
   recoverable for PANW/SKHY. Recommend leaving these as-is and reporting them, since inventing
   replacement content would be fabrication, not a fix. Awaiting direction before touching this
   projection content.

No fallback paths, dual-write, or JSON access were removed. No cleanup performed. Proceeding to
TDD implementation of items 1–2 above.
