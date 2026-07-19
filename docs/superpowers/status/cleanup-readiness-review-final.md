# Cleanup Readiness Review — Final (Updated After Priorities 1-4 + Durability Fix)

Second pass, after the two blockers from the first version of this review were addressed:
`observations.jsonl`/`research/archive/` durability (fixed) and the orphan pointer investigation
(documented, deliberately not fixed — see below). No cleanup, fallback removal, or dual-write
removal has been performed at any point.

## 1. Is the fallback path working?

**Yes, for 116 of 120 original pointers (96.7%)**, unchanged from the prior review — verified at
the real route layer, not just unit-tested. The remaining 4 are root-caused and disposition-
analyzed in `orphan-research-pointer-review.md`: `INTC_DEBUG.md` is dormant (sits on a superseded
projection version no UI path reaches), `PANW`/`SKHY` are live 404s on their current version,
pending an ownership call this review deliberately does not make unilaterally.

## 2. Has rollback been physically tested?

**Yes**, unchanged — `rollback-exercise-report.md`.

## 3. Can research be recovered from `observations.jsonl`?

**Yes, and now durably.** Proven twice with byte-level content parity (§4 of the prior review).
**Resolved this pass:** `observations.jsonl` is now committed to git — it is no longer a
single-worktree, single-disk point of failure. `research/archive/` (the 80 original dated files)
is also now committed, after discovering it had been silently excluded by an unrelated legacy
`.gitignore` rule the entire time. See `observations-jsonl-durability-recommendation.md`.

## 4. Can SQLite be rebuilt from scratch?

**Yes**, unchanged — `intelligence.sqlite` remains correctly gitignored as a genuinely derived
artifact, proven rebuildable with byte-level parity twice this session.

## 5. What must remain?

Unchanged from the prior review, with one item resolved: `observations.jsonl` and
`research/archive/` now remain *durably* (committed), not just present on disk. The 72
pre-existing bare `{TICKER}.md` canonical files, the dual-write/fallback code in `docs.ts`, and
the 3 orphan pointers (pending ownership decision) all still need to remain for the same reasons
stated previously.

## 6. What is safe to retire?

Unchanged — nothing yet. The 144 generated view files are real, verified, and now sit alongside a
durably-committed source, so there is no remaining technical reason to treat them as provisional.

## Is cleanup approved?

**Not yet — but only one narrow, bounded item remains, and it is explicitly not an engineering
decision.**

Of the two blockers identified in the previous version of this review:

1. ~~Commit `observations.jsonl`~~ — **Done this pass**, along with the previously-unknown
   `research/archive/` gitignore gap.
2. **Product decision on `PANW`/`SKHY`/`INTC_DEBUG.md`** — still open, by design. This review
   documented history and current impact (`orphan-research-pointer-review.md`) but did not
   fabricate a fix, since blanking a pointer or deciding not to source replacement research is a
   product call, not a migration-tooling bug.

Once that one decision is made (and implemented, if the decision is to act on it), there is no
remaining technical blocker to cleanup readiness. Rebuild, rollback, fallback correctness, and
data durability are all proven with evidence at this point, not just asserted.
