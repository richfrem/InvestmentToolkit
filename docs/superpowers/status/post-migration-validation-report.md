# Post-Migration Validation Report

Generated: 2026-07-18, in `.worktrees/worktree-phase4a-audit`. Executes the "Rebuild Validation"
and "Rollback Validation" priorities from the Sonnet handoff
(`temp/sonnet-handoff-2026-07-18-post-migration-status.md`). **No cleanup, no fallback removal,
no dual-write removal, and no additional migration was performed** — validation only, per the
handoff's explicit instruction.

---

## 1. Pre-Validation Independent Verification

Before running any validation, every claim in the handoff and its 4 supporting reports was
independently re-checked against the actual repository state (not trusted from the documents
alone):

- `observations.jsonl`: confirmed 80 lines, 812,152 bytes.
- `intelligence.sqlite`: confirmed 80 rows in `intelligence_event`, all `event_type =
  RESEARCH_IMPORT`, all 8 expected tables present (including full FTS5 support tables).
- `research/archive/`: confirmed 80 files (the migrated dated originals, moved not deleted).
- `research/`: confirmed 72 remaining `.md` files (bare `{TICKER}.md` canonical files, from an
  earlier, unrelated `consolidate_research.py` pass — untouched by this migration).
- Projection pointer rewrite: confirmed, via the exact regex the migration script itself uses,
  **zero** remaining dated-shape `researchReport` pointers — matches the report's claim.
- `git status`: two untracked items (`observations.jsonl`, `package-lock.json`) — the real
  migrated ledger is **not yet committed to git**, worth noting as a fragility point until it is.

All of the above matched the handoff's claims exactly. No discrepancy found at this stage.

## 2. Priority 1 — Rebuild Validation (Executed)

1. Backed up `intelligence.sqlite` (1,355,776 bytes, MD5 `d8aa9b0a...`) and `observations.jsonl`
   (MD5 `ad506276...`) to a location outside the repository, before touching anything.
2. Deleted `investment_screener/backend/data/intelligence.sqlite`.
3. Rebuilt via `rebuild_db.run_rebuild('observations.jsonl', 'intelligence.sqlite')`.
   **Result:** `{'ledger_valid_lines': 80, 'projected_rows': 80, 'skipped': 0, 'verified':
   True}`.
4. Confirmed post-rebuild: all 8 tables present, 80 rows in `intelligence_event`, 80 rows in
   `intelligence_event_fts` (parity), FTS `MATCH` query returns real results.
5. **Byte-level content parity**: exported `(event_id, title, body_markdown)` sorted by
   `event_id` from both the pre-rebuild backup and the post-rebuild database and diffed them.
   **Result: `IDENTICAL` — zero differences.** This is the strongest form of verification
   available: not just row counts matching, but every character of every migrated research
   report reproduced exactly from `observations.jsonl` alone.
6. Retrieval tested for the three specified tickers (AAPL, MSFT, ALAB) via
   `query_ledger_research.py --get <ticker>_2026-05-02.md` — all three returned complete, real
   research report content (not stubs).
7. Retrieval tested at the Node/Express layer: built the backend (`npm run build -w backend`),
   then called `queryLatestResearchFromLedger()` directly (the same function `docs.ts`'s route
   handler calls) for all three tickers — all three returned `OK` with real content lengths
   (3842 / 16264 / 3675 chars).
8. Full test suite: `run_tests.py` (T0/T0.5 gate) — all green. `pytest
   investment_screener/backend/tests/py_services/` — 1212 passed, 21 failed (all 21 in
   `test_fetch_consensus_for_ticker_*`, `test_grade_earnings_expectations_*`,
   `test_get_earnings_context_*`, `test_earnings_expectation_claim_round_trips_ledger.py`,
   `test_evolution_event_correlation_report_generates_summary.py` — earnings/yfinance-network
   modules, unrelated to the research ledger, same pre-existing failure pattern independently
   confirmed multiple times earlier in this effort). All 84 intelligence/migration-specific
   tests pass. `npm run test -w backend` — 49 passing, 1 failing (`zod-schemas.spec.ts`, the
   same pre-existing production-data-validation failure confirmed unrelated in an earlier PR
   review this session).

**Rebuild validation: PASSED.** The system can be fully and correctly reconstructed from
`observations.jsonl` alone, with verified byte-level fidelity, and both the Python and
Node/Express retrieval layers work correctly against the rebuilt database.

## 3. Priority 2 — Rollback Validation (Not Executed, Reviewed Only)

The execution report's documented rollback procedure (`git checkout --
investment_screener/backend/data/projections/`; move files back from `archive/`; delete
`observations.jsonl`/`intelligence.sqlite`) was reviewed for correctness but **not run** — this
report's Priority 1 already proved the forward path (rebuild from ledger) works with verified
parity, and actually executing a full rollback would require re-doing the migration afterward
to restore current state, which is more disruptive than the validation warrants right now.
**Flagging as not executed, not as passed** — if you want the rollback path physically
exercised (not just reviewed), that's a distinct next step.

## 4. New Finding: Broken Fallback Pointers (Not Previously Reported)

Independent verification during this validation surfaced a real defect **not mentioned in any
of the 4 prior reports**:

- All 118 rewritten `researchReport` pointers now point to `{TICKER}.summary.md` — but **no
  `.summary.md` file has ever been generated anywhere in this repository** (`view_generator.py`,
  built in PR #77, has never been run for real either — confirmed: zero `.summary.md`/
  `.timeline.md` files exist on disk). The actual canonical files on disk are named bare
  `{TICKER}.md` (e.g. `AAPL.md`, not `AAPL.summary.md`).
- `docs.ts`'s `CANONICAL_FILENAME_RE` (`/^[A-Z0-9.-]{1,10}\.(summary|timeline)\.md$/`) only
  recognizes the `.summary.md`/`.timeline.md` shape — it does not recognize the bare
  `{TICKER}.md` shape that actually exists on disk. Requesting one of the 72 canonical files
  directly by its real filename would be **rejected by the route's own filename validation**
  (400 error), separate from the pointer issue.
- 2 additional pointers were found not matching either the dated or `.summary.md` shape:
  `INTC.json` version 2 points to `INTC_DEBUG.md` (a file that has never existed anywhere in
  this repository — likely stale/leftover test data unrelated to this migration), and
  `OKLO.json` version 1 points to the **full path**
  `investment_screener/backend/data/research/OKLO_2026-05-02.md`, which no longer exists at
  that location (the file was correctly migrated and moved to `research/archive/OKLO_2026-05-02.md`
  by this migration — the pointer wasn't caught because it was stored as a full path rather than
  a bare filename, which the rewrite script's regex doesn't match).

**Current real-world impact: none, currently masked.** The primary retrieval path (ledger
lookup) succeeds for all 80 migrated tickers, including OKLO — confirmed by direct test. The
broken pointers only matter as a **fallback** path, and the fallback currently never triggers
because the primary path always succeeds for these tickers. This is a latent defect, not an
active outage.

**This was not caught by any of the 4 prior reports**, which only checked pointer *rewrite
count* (118) against pre-migration count (120), not whether the rewritten targets actually
exist on disk or match the route's own filename validation regex.

## 5. Priority 3 — Cleanup Readiness Assessment

Per the handoff's explicit instruction, **no cleanup was performed or recommended for
execution**. Direct answers to the four assessment questions, based on this session's evidence:

- **What still depends on legacy paths?** The fallback path in `docs.ts` (broken per §4, but
  currently unused since the primary path always succeeds for migrated tickers). The 72 bare
  `{TICKER}.md` canonical files are still the only artifact serving non-ledger-migrated research
  requests.
- **What can safely be retired?** Nothing yet — the fallback path, though currently dormant, is
  the only safety net if the ledger ever has a gap, and it's currently broken in a way that
  hasn't been fixed or tested. Retiring the dual-write/fallback before fixing §4 would remove
  the safety net without confirming a working replacement exists.
- **What must remain?** The 80 archived dated files (`research/archive/`), the 72 bare canonical
  files, and `observations.jsonl` (authoritative source) all must remain, per the existing
  cleanup blocker.
- **Is rollback sufficient?** The rollback *procedure* is documented and reviewed as logically
  correct, but not physically exercised in this pass (§3) — "sufficient" cannot be confirmed
  with full confidence until it's actually run once.

**Cleanup readiness: NOT READY.** The §4 finding is a real gap that should be resolved (fix the
pointer targets and/or generate the actual `.summary.md`/`.timeline.md` files, or update
`CANONICAL_FILENAME_RE` to also recognize bare `{TICKER}.md`) and the rollback procedure should
be physically exercised at least once, before cleanup readiness can honestly be called complete.

---

## Summary

| Question | Answer |
|---|---|
| Does the system rebuild correctly from `observations.jsonl`? | **Yes** — verified byte-for-byte identical content, not just row counts |
| Does retrieval work after rebuild (Python + Node/Express)? | **Yes** — verified for AAPL, MSFT, ALAB at both layers |
| Does the full test suite pass? | **Yes**, modulo the same pre-existing unrelated failures confirmed throughout this whole effort (21 earnings/yfinance Python tests, 1 zod-schemas TS test) |
| Was a new defect found? | **Yes** — 118+2 broken fallback pointers (§4), currently dormant/masked, not previously reported |
| Was rollback physically exercised? | **No** — reviewed only |
| Is cleanup ready to begin? | **No** — §4 needs resolution and rollback needs physical exercise first |
