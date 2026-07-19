# Cleanup Execution Plan — SQLite Intelligence Ledger Migration

Retirement inventory for every asset this migration touches. Built from
`cleanup-readiness-review-final.md`, `sqlite-ledger-migration-final-certification.md`,
`intelligence-ledger-artifact-inventory.md`, and `orphan-research-pointer-review.md`, plus a
direct repo search for deprecation markers, stray temp/backup files, and dead code in every
script/route this migration touches — none found. Classification uses evidence gathered this
session, not "looks legacy" heuristics.

## Classification Table

| Path | Reason it might look retirable | Replacement | Proof replacement is operational | Rollback method | Classification |
|---|---|---|---|---|---|
| `investment_screener/backend/data/observations.jsonl` | N/A — this *is* the replacement | — | — | Git history (now committed) | **RETAIN AS AUTHORITATIVE SOURCE** |
| `investment_screener/backend/data/research/archive/*.md` (80 files) | "Old" dated research, superseded by the ledger | `observations.jsonl` `body_markdown` | Byte-level parity proven twice (rebuild + rollback exercise) | Already the rollback target itself — retiring it would break the documented rollback procedure | **RETAIN AS AUTHORITATIVE SOURCE** (also functions as the rollback anchor) |
| `investment_screener/backend/data/research/{TICKER}.summary.md` / `.timeline.md` (144 files) | "Generated," sounds disposable | Regenerable from `observations.jsonl` via `render_all_ticker_views.py` | Proven this session — but `docs.ts` currently reads these from disk directly for canonical-shaped requests, not via a live ledger query | Delete + re-run `render_all_ticker_views.py` | **RETAIN FOR COMPATIBILITY** — the live route depends on the file existing on disk today; retiring it reintroduces the exact 404 bug fixed this session |
| `investment_screener/backend/data/research/{TICKER}.md` (72 bare canonical files) | Pre-existing, unrelated to this migration, "probably legacy" | None — no ledger coverage exists for these tickers' canonical content | N/A | N/A | **RETAIN FOR COMPATIBILITY** — currently the only content for any ticker not covered by the ledger; also currently unreachable via the route at all (separate, pre-existing gap, out of this migration's scope — not a reason to remove it) |
| `investment_screener/backend/data/projections/*.json` — `PANW`/`SKHY`/`INTC_DEBUG.md` pointers | Broken, look like migration debris | N/A | N/A | N/A | **RETAIN FOR BUSINESS DECISION** — confirmed pre-existing (predate this migration), not caused by it; disposition documented in `orphan-research-pointer-review.md`, no fix applied |
| Dual-write JSON paths in `ta_sweep_batch.py`, `compute_conviction_scores.py`, `daily_brief.py`, `dailybrief.ts`, `docs.ts` | "The SQLite path works now, why write JSON too?" | SQLite ledger path (already primary read path in each) | Each migrated and validated this cycle | Removing dual-write removes the fallback safety net | **RETAIN FOR COMPATIBILITY** — explicitly protected: "Do NOT remove dual-write" has been a standing instruction across every phase of this effort, not just this pass |
| Fallback/disk-read code paths in `docs.ts`, `daily_brief.py`, etc. | Ledger path is now proven correct | Ledger query | Proven | Removing fallback removes the safety net proven by the rollback exercise | **RETAIN FOR COMPATIBILITY** — same standing instruction |
| `investment_screener/backend/py_services/rebuild_db.py`, `migrate_research_to_ledger.py`, `migrate_research_report_pointers.py`, `render_all_ticker_views.py` | "One-time migration scripts, done now" | N/A | N/A | Explicitly needed to re-run the physically-exercised rollback/rebuild procedure | **RETAIN AS AUTHORITATIVE TOOLING** — required for reconstruction, explicitly protected by this phase's own "Do NOT Remove" list |
| `evolution_events.py` | Still JSON-only, not ledger-migrated | Would be `intelligence_event` if migrated | Not migrated | N/A | **RETAIN FOR BUSINESS DECISION** — explicitly out of scope this cycle, needs its own ADR per standing instruction |
| `docs/superpowers/status/*.md` (all prior validation/status reports) | Superseded by the final certification report | `sqlite-ledger-migration-final-certification.md` | This document explicitly says prior reports "remain valid as historical evidence trails" | Git history | **Out of scope for this exercise** — these are documentation/evidence records, not data or tooling assets; the "Do NOT Remove" list in this phase's instructions is scoped to data/tooling, and no instruction has asked for documentation pruning |
| `ARCHIVE/questrade/*` | Already-retired, unrelated integration | N/A (already retired prior to this session) | N/A | Now git-tracked (this session, separately) | **Out of scope for this exercise** — pre-existing retirement from an unrelated integration, already handled; brought under version control this session as a durability fix, not as part of this migration's retirement inventory |

## Verdict

**Zero items classify as `SAFE TO RETIRE`.**

Every artifact this migration created or touched is either the authoritative source, tooling
required to prove/rebuild/roll back that source, a file the live application currently reads
directly (so removing it reproduces the exact bug this session fixed), or a pending business
decision explicitly excluded from cleanup. This isn't a failure to find candidates — it's the
direct consequence of the dual-write/fallback architecture this whole effort has deliberately
kept intact at every phase, per repeated explicit instruction. Retiring the dual-write or
fallback paths is a distinct, larger decision (removing the safety net entirely) that hasn't
been asked for in this phase and isn't attempted here.

## Step 3 Disposition

No execution needed — there is nothing in the `SAFE TO RETIRE` category to move or remove.
Proceeding directly to Step 4 (validation) to confirm nothing has regressed since the last
certified state, and Step 5 (final report) to close out this phase.
