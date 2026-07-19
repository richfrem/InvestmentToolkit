# Orphan Research Pointer Review

Covers the 3 pointers found during this migration's fallback-path validation that are **not**
fixable by migration tooling: `INTC_DEBUG.md`, `PANW`, `SKHY`. History and current impact only —
no speculative fixes applied. Disposition is a product/ownership decision.

---

## INTC_DEBUG.md

**History:** `investment_screener/backend/data/projections/INTC.json` version 2 (`analyzedAt:
2026-02-15T15:25:31.502Z`) has `aiThesis.researchReport = "INTC_DEBUG.md"`, `model:
"debug-model"`, `rationale: "Testing save with new fields"`. Confirmed via `git show
f860b29e^:...INTC.json` that this exact value predates the SQLite migration entirely — it is not
something this migration created or touched. No file named `INTC_DEBUG.md` has ever existed
anywhere in this repository's git history. This is leftover data from manually exercising the
projection-save feature during development, saved into production data by mistake.

**Current impact: none, currently.** `INTC.json` holds 4 versions (2, 8, 9, 10).
`ThesisService.getLatestAIProjection()` sorts descending by the `version` number and serves only
the highest (version 10, `analyzedAt: 2026-05-02T23:05:00Z`) — never version 2. No frontend
version-history browser exists (searched `investment_screener/frontend/src` — no
version-selector or history UI found), so there is currently no code path a user can reach that
requests `INTC_DEBUG.md`. This is dead, dormant data, not a live bug.

**Recommended disposition:** low priority. Since it's unreachable in normal use, the only
practical concern is data hygiene — a stray debug entry sitting inside real production data. No
urgency to act.

---

## PANW

**History:** `PANW.json` holds 2 versions (2, 3), both with `aiThesis.researchReport =
"PANW.summary.md"`. Confirmed via `git show f860b29e^:...PANW.json` that this migration's
predecessor state already had `PANW_2026-05-02.md` (a *dated* shape) as the pointer — meaning the
pointer-rewrite script behaved correctly (a dated reference was rewritten to canonical shape, as
designed). The problem predates that: `PANW_2026-05-02.md` has never existed anywhere in this
repo's git history — not in `research/`, not in `research/archive/`, no matching
`RESEARCH_IMPORT` event in `observations.jsonl`. This is an orphaned reference from before any
SQLite work began; the underlying research content this pointer was supposed to name was never
actually saved as a file, for reasons this investigation cannot determine from repo history
alone.

**Current impact: live.** Version 3 is PANW's highest version — the one
`getLatestAIProjection()` actually serves. A user opening PANW's Deep Dive / research modal today
gets a 404, on the *current*, default-displayed version, not a buried historical one.

**Recommended disposition:** needs an ownership decision. Two honest options, neither of which
this review will pick for you: (a) clear `researchReport` from the current version so the UI
correctly shows "no research available" instead of erroring, or (b) source and add real PANW
research content going forward via the standard `event_store` → `view_generator` flow. Option
(a) is a one-line, reversible data fix if you want it done; this review deliberately stops short
of doing it since "the pointer should just be blanked" is a product call, not an engineering one.

---

## SKHY

**History:** `SKHY.json` holds 1 version (1), `aiThesis.researchReport = "SKHY.summary.md"`.
Same pattern as PANW: pre-migration state (`git show f860b29e^:...`) already had
`SKHY_2026-07-13.md` as the pointer, confirmed never to have existed as a real file anywhere in
this repo's history. SKHY is a newer entrant to the corpus (`2026-07-13` is a much more recent
date than the other ~May 2026 entries) — this looks like a case where the projection was created
and a research-report filename was recorded as a placeholder/intent, but the actual research
write-up was never produced or saved.

**Current impact: live.** SKHY has only one version, so it is unconditionally the "latest" one
served — same 404-on-default-view impact as PANW.

**Recommended disposition:** same two options as PANW — blank the pointer, or produce the
missing research content. Given the recency of this entry, it may be more likely that real
research is still forthcoming for SKHY rather than permanently lost, unlike PANW where the
implied source file's absence has no recent-activity explanation. This review cannot determine
intent from the data alone — flagging for the same ownership decision.

---

## Summary Table

| Pointer | Predates migration? | On current/latest version? | Live user impact | Recommended action |
|---|---|---|---|---|
| `INTC_DEBUG.md` | Yes | No (superseded by v8/9/10) | None — unreachable | Low priority; data hygiene only |
| `PANW.summary.md` (orphan) | Yes | Yes (v3 is latest) | 404 on default view | Ownership decision: blank pointer or source content |
| `SKHY.summary.md` (orphan) | Yes | Yes (only version) | 404 on default view | Ownership decision: blank pointer or source content |

None of these three were caused by the SQLite migration. All three predate it and were exposed,
not created, by this validation pass.
