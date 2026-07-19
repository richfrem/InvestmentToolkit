# SQLite Intelligence Ledger Migration — Final Certification

Certifies the state of the migration as of this session's post-migration validation and
correction pass, on branch `worktree-phase4a-audit`. Supersedes prior status documents as the
current record; those documents (`master-status-and-outstanding-work.md`,
`post-migration-validation-report.md`, etc.) remain valid as historical evidence trails, not as
the current picture.

## 1. Architecture Completion — Done

Per ADRs 026/027/028: event-sourced ledger (`observations.jsonl`, authoritative, append-only) →
derived SQLite read-model (`intelligence.sqlite`, WAL mode, FTS5) → generated Markdown views
(`{ticker}.summary.md`/`.timeline.md`). Shared repository/service layer in
`py_services/intelligence/` (`db_client.py`, `event_store.py`, `event_repository.py`,
`instrument_repository.py`, `replay_ledger.py`, `view_generator.py`) is the sole owner of all
`intelligence_event` SQL, per ADR-028's anti-duplication rule — verified no other script opens
its own connection to that table.

## 2. Consumer Adoption Completion — Substantially Done

From the Task 18 consumer inventory (151 real code consumers, 0 `UNKNOWN_REQUIRES_REVIEW`):
`USES_LEDGER_REPOSITORY: 17`, `USES_GENERATED_VIEW: 2`, `OUT_OF_SCOPE: 1`,
`MIGRATION_REQUIRED: 1` (`evolution_events.py` — intentionally deferred pending an ADR decision,
per explicit user instruction not to touch it in this pass). Migrated this cycle: `ta_sweep_batch.py`,
`compute_conviction_scores.py`, `daily_brief.py`, `dailybrief.ts`, `daily-loop-agent.md`,
`docs.ts`.

## 3. Research Migration Completion — Done, With One Correction

80 dated research files migrated to `observations.jsonl` as `RESEARCH_IMPORT` events, replayed
into `intelligence.sqlite` (80/80 verified), 119 `aiThesis.researchReport` pointers rewritten
from dated to canonical shape (118 in the original pass + OKLO's full-path pointer, caught by
this session's regex fix). **Correction made this session:** the historical migration only
performed the ledger-append half of the intended workflow; the render half
(`view_generator.render_ticker_views()`) was never run for the backfilled tickers, so every
rewritten pointer 404'd in the live app. Closed via a new backfill script — see §5.

## 4. Rebuild Validation — Proven, Twice, With Byte-Level Parity

Not row-count validation — content validation. First proof (earlier this session): deleted
`intelligence.sqlite`, rebuilt from `observations.jsonl`, diffed `(event_id, title,
body_markdown)` between backup and rebuild — zero differences. Second, independent proof (this
pass's rollback exercise, §6): a full rollback-then-forward-remigration cycle, verified
content-identical at every layer (DB, JSONL, projections, generated views) using key-based
comparison (`(ticker, effective_at) → body_markdown`) that doesn't depend on `event_id` staying
stable across independent migration runs.

## 5. Fallback Validation — Fixed and Proven (Was Previously Mis-Reported)

The prior validation pass concluded the fallback path was "dormant, masked, no current impact."
That conclusion was wrong: it tested `queryLatestResearchFromLedger()` directly with the old
dated filename, not the filename the frontend actually requests. Tracing the real path
(`DeepDiveModal.tsx` → `aiThesis.researchReport` → `GET /api/research/:filename`) showed
`docs.ts`'s ledger-query gate only accepts the dated-filename shape, so every rewritten
`.summary.md` pointer skipped the ledger entirely and 404'd against files that had never been
generated. This was a live, active bug affecting all 73 unique migrated tickers.

**Fixed this session:** added `list_tickers_with_active_event_type()` to the repository layer
and `render_all_ticker_views.py` (TDD, new tests), ran it for real — 72 tickers, 144
`.summary.md`/`.timeline.md` files generated and verified readable through the exact live route
logic. Also fixed the OKLO full-path pointer bug in `migrate_research_report_pointers.py`
(anchored regex didn't match path-qualified values) — covered by a new regression test.

**Current state: 116 of 120 original pointers resolve correctly** (96.7%). The remaining 4
(`PANW` ×2, `SKHY`, `INTC_DEBUG.md`) are confirmed via git history to predate this migration
entirely — see `orphan-research-pointer-review.md` for full disposition analysis.

## 6. Rollback Validation — Physically Exercised, Not Just Reviewed

Backed up current state, rolled back to the pre-migration commit (`git checkout aed7fd12 --
projections/`, moved archive files back, removed generated views + ledger + DB), verified
byte-identical parity with pre-migration state, and confirmed the pre-migration disk-fallback
path genuinely works with the ledger database completely absent (no crash — `docs.ts`'s
try/catch degrades to `null` and falls through to disk, exactly as designed). Then re-ran the
full forward migration and verified content-level parity against the pre-rollback backup at
every layer. Full detail: `rollback-exercise-report.md`.

## 7. Durability Fix (Found During Certification Prep)

`observations.jsonl` — the sole authoritative source, and the permanent store every future
research/technical-sweep event already writes to per the standing SKILL.md workflows — was
untracked in git. Separately, `research/archive/` (the 80 original dated files the migration
promised not to delete) turned out to be silently excluded by an unrelated, pre-existing
`.gitignore` rule that predates this migration. Both fixed this session: gitignore scoped with an
explicit negation, both committed. See `observations-jsonl-durability-recommendation.md`.

## 8. Remaining Blockers

1. **Product decision needed on `PANW`/`SKHY`/`INTC_DEBUG.md`** (§5, full detail in
   `orphan-research-pointer-review.md`). `INTC_DEBUG.md` is dormant (superseded version, no
   version-history UI reaches it) — low priority. `PANW`/`SKHY` are on each ticker's
   currently-served version — live 404s, needs an ownership call (blank the pointer vs. source
   real content).
2. **`evolution_events.py`** — intentionally not migrated this cycle, per explicit standing
   instruction; needs its own ADR before any migration work begins.
3. **72 pre-existing bare `{TICKER}.md` canonical files** in `research/` (unrelated to this
   migration, from an earlier `consolidate_research.py` pass) are currently unreachable through
   `/api/research/:filename` under any pointer shape — `CANONICAL_FILENAME_RE` doesn't match bare
   `.md`. Predates this migration, out of this pass's scope, worth its own review.

## 9. Cleanup Readiness Verdict

**Not yet approved, but the technical case is complete.** Every item that would have made cleanup
irresponsible — unproven rebuild, unproven rollback, a broken fallback path, undurable source
data — is now proven or fixed with evidence, not assertion. What remains (§8) are bounded
product/ownership decisions, not open engineering risk. Re-assessed in
`cleanup-readiness-review-final.md`.

## 10. Test Evidence

Full backend suite, this pass's final run: 1216 passed, 22 failed (all 22 confirmed pre-existing
and unrelated — earnings/yfinance-network tests and one cwd-fragile test, stable across every run
this session), 2 xfailed. All 31 intelligence/migration-specific tests pass. No regressions
introduced by any fix in this pass.
