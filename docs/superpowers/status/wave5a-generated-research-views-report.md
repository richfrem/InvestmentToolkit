# Wave 5A — Generated Research Views: Exit Report

**Branch:** `worktree-wave5a-generated-research-views`
**Base:** `main` @ `e49de1ec`
**Commits:** `9117dc3c`, `51b40c8e`

## Scope

Per the overall plan (`docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`
§ Wave 5A) and ADR-029: `docs.ts`'s `GET /api/research/:filename` route had a dead legacy-filesystem
fallback branch for dated research report filenames (`TICKER_YYYY-MM-DD.md`). Remove it and query
`intelligence_event` unconditionally for that shape.

## Pre-Implementation Findings (re-verified against real code/data, not the plan's one-liner)

- **Producer already live:** `plugins/stock-valuation/skills/stock-research/SKILL.md` writes
  `RESEARCH_IMPORT` events via `python3 -m intelligence.event_store` — not a stale one-time
  migration script. No producer work needed this wave.
- **Ledger populated:** main checkout's `investment_screener/backend/data/intelligence.sqlite` has
  exactly 80 `RESEARCH_IMPORT` / `ACTIVE` rows (matches ADR-029's "80 research reports").
- **Fallback confirmed fully dead:** zero files on disk match the DATED shape
  (`TICKER_YYYY-MM-DD.md`) in `investment_screener/backend/data/research/` — the fallback could
  only ever return stale/wrong data or mask a true 404, never a real answer.
- **`.summary.md`/`.timeline.md` (CANONICAL shape) correctly out of scope:** these are
  `GENERATED_FROM_SQLITE` render-to-disk views (`py_services/intelligence/view_generator.py`,
  itself reading `intelligence_event`), not migration debt. Their fs read path is unchanged.
- **403 path-traversal check was provably unreachable:** both `DATED_FILENAME_RE` and
  `CANONICAL_FILENAME_RE` are closed character classes (`[A-Z0-9.-]{1,10}`) with no `/` possible —
  confirmed by both the task reviewer and the final whole-branch reviewer independently reading the
  regex definitions. Dropped as part of this wave's debt-removal, not carried forward.

## Wave KPI Table

| Metric | Before | After |
|---|---|---|
| JSON/JSONL files in this domain | 0 (already ledger-backed at the data layer; this was a code-path issue, not a file-migration one) | 0 |
| Dead fallback branches in `docs.ts` | 1 (fs fallback for dated research filenames) | 0 |
| Producers on SQLite | 1 (`stock-research` skill, already live pre-wave) | 1 (unchanged) |
| Consumers reading SQLite unconditionally, no fallback | 0 (conditional w/ fs fallback) | 1 (`GET /research/:filename`, dated path via `getResearchReport`) |
| Real fs reads remaining (by design, unrelated domain) | CANONICAL view files | CANONICAL view files (unchanged, correct) |
| New exported/testable function | — | `getResearchReport(filename, dbPath?, researchDir?)` |
| New unit tests | — | 5 (invalid shape, dated-found, dated-not-found-no-fallback regression, canonical-found, canonical-not-found) |

## Producer/Consumer Cutover Table

| Component | Pre-wave | Post-wave |
|---|---|---|
| Producer: `stock-research` skill → `intelligence.event_store` | Already writes `RESEARCH_IMPORT` to SQLite | Unchanged — confirmed still the sole live producer |
| Consumer: `docs.ts` `GET /research/:filename` (dated shape) | Ledger query first, fs fallback on miss/error | Ledger query only; `not_found` on miss, no fs read |
| Consumer: `docs.ts` `GET /research/:filename` (canonical shape) | fs read (never touches ledger) | Unchanged — fs read, correct for `GENERATED_FROM_SQLITE` views |
| Consumer: `docs.ts` `GET /research` (list route) | Combines ledger + fs listing | **Unchanged, out of scope this wave** — still legitimately falls back per its own docstring |

## Real Bugs Found and Fixed

None found beyond the debt this wave targeted — the code was functioning correctly for real
traffic (0 dated files on disk means the fallback branch was already unreachable in practice); the
risk was latent (a future stale file placed on disk, or a ledger read error being silently masked
as a served stale file) rather than an active production bug.

One log-message accuracy fix from the final review's Minor finding: `queryLatestResearchFromLedger`'s
error log said "falling back," which became inaccurate once the dated-path fallback was removed
(commit `51b40c8e`). The list route's identical-looking log for `queryResearchListFromLedger` was
left unchanged — it still legitimately falls back to fs.

## Validation Results

- Targeted suite: `npm run test -w backend -- --grep "getResearchReport|DATED_FILENAME_RE|ledger query helpers"` — **10/10 passing**.
- Full backend suite: `npm run test -w backend` — **133 passing / 2 failing**, matching the
  documented pre-existing baseline exactly (`zod-schemas.spec.ts`, `InvestmentRepository`
  real-sqlite parity test) — confirmed unrelated to this change, no new failures.
- This wave made **no real data migration write** — there is no gitignored JSON/JSONL file for
  this domain to migrate (data was already in `intelligence.sqlite` pre-wave); the
  worktree-vs-main DB verification requirement from CLAUDE.md pitfall #29 / the kickoff prompt's
  Setup step does not apply here. Confirmed: no script in this diff opens a new SQLite connection
  or writes to `domain_model.sqlite`/`intelligence.sqlite`.

## Archive Evidence

Not applicable — no JSON/JSONL file existed for this domain to archive. The change is a pure
code-path fix in an already-SQLite-backed route.

## Review Trail

- Task 1 review (subagent-driven-development task reviewer): Spec ✅, Task quality Approved, no
  findings.
- Final whole-branch review: Ready to merge — Yes. No Critical/Important findings. One Minor
  finding (stale "falling back" log wording) — fixed in `51b40c8e`, re-verified with both the
  targeted suite and the full suite above.

## Rollback Instructions

`git revert 51b40c8e 9117dc3c` restores the fs-fallback branch and the unreachable 403 check.
No data changes to reverse — this wave touched only route/test TypeScript files.

## Commit List

- `9117dc3c` — fix(docs.ts): remove dead fs-fallback for dated research reports (ADR-029/Wave 5A)
- `51b40c8e` — fix(docs.ts): drop stale 'falling back' wording from getResearchReport's error log

## Remaining Exceptions

None new. Pre-existing test-suite baseline exceptions (`zod-schemas.spec.ts`,
`InvestmentRepository` real-sqlite parity) unchanged, tracked in the overall plan's Hard-Stop
Conditions #7.
