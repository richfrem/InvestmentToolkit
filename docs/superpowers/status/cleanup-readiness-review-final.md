# Cleanup Readiness Review — Final (New Priority 4)

Assessment only. No cleanup, fallback removal, or dual-write removal was performed. Answers the
6 questions from the handoff, using evidence from this session's post-migration validation
(`post-migration-validation-report.md`), fallback-path fix
(`fallback-path-investigation-and-recommendation.md`), and rollback exercise
(`rollback-exercise-report.md`).

## 1. Is the fallback path working?

**Yes, for 116 of 120 original `researchReport` pointers (96.7%)** — up from 0 at the start of
this pass. Verified end-to-end at the real route layer (not just unit-tested in isolation):
`AAPL.summary.md` and `OKLO.summary.md` both confirmed readable through the exact disk-fallback
logic `docs.ts` executes.

The remaining 4 pointers are **not fixable by migration tooling** — confirmed via git history to
be pre-existing, orphaned references that predate this migration entirely (no backing file has
ever existed for any of them, in this repo's history):
- `PANW.json` versions 2, 3 → `PANW.summary.md`
- `SKHY.json` version 1 → `SKHY.summary.md`
- `INTC.json` version 2 → `INTC_DEBUG.md` (confirmed leftover manual test data, not a real
  research report)

These need a product decision (remove the pointer / accept the gap), not a migration fix — see
§5.

## 2. Has rollback been physically tested?

**Yes.** Not reviewed-only this time — executed for real: backed up, rolled back to the
pre-migration commit, verified byte-identical parity with pre-migration state and that the
pre-migration disk-fallback path genuinely serves content with the ledger database absent
(confirmed no crash, graceful `null` return, correct fallback), then re-ran the forward
migration and verified content-level parity against the pre-rollback backup at every layer (DB,
JSONL, projections, generated views). Full detail: `rollback-exercise-report.md`.

## 3. Can research be recovered from `observations.jsonl`?

**Yes, with byte-level proof**, established earlier in this validation pass (see
`post-migration-validation-report.md` §2): deleted `intelligence.sqlite`, rebuilt from
`observations.jsonl` alone, and diffed `(event_id, title, body_markdown)` between the pre-delete
backup and the rebuilt DB — **zero differences**. This was independently re-confirmed during
this pass's rollback exercise via a second, differently-constructed rebuild (full
migrate→rebuild→pointer-rewrite→view-render cycle from a rolled-back starting state), again with
zero content differences.

**However — a real risk found during this pass, not previously reported**:
`observations.jsonl`, the single authoritative source for the entire migrated research corpus,
is **not gitignored but also not committed** — it exists only as an untracked file in this
worktree checkout. It is not durably protected by git history the way every other artifact in
this migration is. `package-lock.json` is in the same state, unrelated to this migration. This
needs a decision before cleanup: commit `observations.jsonl` (recommended — it is the one thing
this whole architecture is built to treat as authoritative) or explicitly gitignore it if it's
meant to be regenerated/managed some other way. Right now it is neither, which is the fragile
middle state.

## 4. Can SQLite be rebuilt from scratch?

**Yes**, same evidence as §3 — `intelligence.sqlite` is fully derivable from
`observations.jsonl` via `rebuild_db.run_rebuild()`, proven twice this session with independent
byte-level content comparisons, not just row counts. `intelligence.sqlite` is correctly
gitignored (confirmed) — it is treated as a derived artifact, consistent with the architecture.

## 5. What must remain?

- `observations.jsonl` — authoritative source. Must remain (and should be committed — see §3).
- `research/archive/` (80 dated originals, moved not deleted by the migration) — must remain
  until there is independent confidence the ledger is the durable long-term source; currently
  the only human-readable copy of the original dated research outside the DB/JSONL.
- The 72 pre-existing bare `{TICKER}.md` canonical files in `research/` — unrelated to this
  migration (from an earlier `consolidate_research.py` pass), still the only content for any
  ticker not covered by the ledger, and still **not servable through the route at all**
  (`CANONICAL_FILENAME_RE` doesn't match bare `.md`) — this was true before this migration and
  remains true; out of this pass's scope but worth flagging since it means those 72 files are
  currently unreachable via `/api/research/:filename` under any pointer shape.
- The `PANW`/`SKHY`/`INTC_DEBUG` broken pointers — until a product decision is made (§1), leave
  as-is; deleting them would be silent data loss of the *pointer*, and there's no real content to
  recover behind them.
- Dual-write and fallback code paths in `docs.ts` — explicitly still needed: they are what serves
  4 of the corpus's edge cases correctly today, and needed as the safety net if a future ledger
  gap appears.

## 6. What is safe to retire?

**Nothing yet, with one narrow exception worth naming:** the 144 generated
`.summary.md`/`.timeline.md` files are now real, verified-correct, checked-in artifacts — once
`observations.jsonl` is committed (§3) and this branch merges, there is no remaining
justification for treating them as provisional. Everything else — the archived dated originals,
the bare canonical files, the dual-write/fallback code — is still load-bearing per §5.

## Is cleanup approved?

**No — but the primary blocker from the last review (broken fallback pointers) is resolved.**
Two items remain before cleanup can be responsibly approved:

1. **Commit `observations.jsonl`** (and decide on `package-lock.json` separately, unrelated).
   This is the one concrete, low-risk action item this review surfaces — everything else is
   already verified working.
2. **Product decision on PANW / SKHY / INTC_DEBUG** (§1) — small, bounded, does not block
   anything else.

Once those two are resolved, the technical case for cleanup readiness is complete: rebuild is
proven, rollback is proven, the fallback path works for the overwhelming majority of the corpus
with the remainder root-caused and explained, and no data loss occurred at any point in this
validation-and-fix pass.
