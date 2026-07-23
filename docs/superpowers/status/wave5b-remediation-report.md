# Wave 5B Remediation — Closing the Spec's Real Validation Bar

**Trigger:** Wave 5B's own plan (`docs/superpowers/plans/2026-07-22-wave5b-ta-sweep-results.md`)
invented a narrower, self-defined "Definition of Done" instead of copying the design spec's real
9-item one, and omitted the spec's §5 Validation Strategy checklist, a required "Hybrid Exit
Criteria" section, and a required "Context Bundle Completion Bar" section. All six task-level
reviews and the final whole-branch review correctly checked the diff against the plan as written
— the gap was upstream, in what the plan asked them to check, not in review rigor. Full root
cause logged as Map Debt (`.agent/map-debt.md`, "Wave 5B — plan omitted the spec's real
Validation Strategy and Definition of Done" entry, 2026-07-22).

This report closes the four items that were skipped, with evidence for each.

## 1. Real-cycle parity test (design spec §5: "run both paths in parallel for at least one full
real-world cycle... and diff row-for-row")

Ran one real, live `ta_sweep_batch.py` sweep against the user's real TradingView Desktop CDP
connection (port 9222, confirmed reachable) with `--save-results` to capture a flat-JSON snapshot
of that run's output **alongside** its now-unconditional SQLite/ledger write — the exact "both
paths in parallel" comparison the spec asks for, using the two write modes Task 4 (already
merged) made available.

- Real scan date: `2026-07-23`. Real ticker count: **79** (holdings ∪ watchlist, confirming
  Task 0's scan-universe expansion is live and correct in production).
- Diffed every ticker's full payload, field-for-field, between the JSON export and the
  `intelligence_event.payload_json` rows for the same `effective_at` date:
  - Missing from DB (present in JSON, absent in SQLite): **0**
  - Extra in DB (present in SQLite, absent in JSON): **0**
  - Field-level mismatches across all 79 matched tickers: **0**
- Result: **byte-identical parity**, both paths in agreement for every ticker on a real, live
  scan.
- The temporary JSON export (`temp/wave5b_parity_check.json`) was deleted after the diff — it was
  a one-time comparison artifact, not a retained file (consistent with Task 4's design: JSON
  export is opt-in/ad-hoc, never a source of truth).

## 2. Rollback exercise, physically executed (design spec §5: "physically exercise rollback at
least once per domain before declaring the wave done... restore from ARCHIVE/, revert
producer/consumer commits, confirm the app runs correctly against the old file again")

Performed in an isolated, throwaway git worktree (branch `worktree-wave5b-rollback-exercise-
throwaway`), never touching `main` or the real production files:

1. `git revert --no-commit` all 7 Wave 5B commits (`2921e34c` through `08b0b6fc`) — reverted
   cleanly, **zero conflicts**. The `git mv` archive step reversed automatically, restoring
   `ta-sweep-results.json` to its original path from `ARCHIVE/`.
2. Ran the reverted (pre-wave) `compute_conviction_scores.py::_load_ta()` pointed at a
   deliberately nonexistent DB path, to force its old JSON-fallback branch:
   - **26 tickers loaded**, `staleness_days: 12` — correctly computed from the restored file's
     real `timestamp` field (`2026-07-10`), proving the fallback genuinely re-reads the restored
     file's real content, not stale/cached state.
3. Ran the full pre-wave test suite for the affected files against this reverted state:
   `test_compute_conviction_scores.py` + `test_daily_brief_ta_sweep_delegates.py` +
   `test_ta_sweep_batch.py` — **43/43 passing**.
4. Discarded the entire throwaway worktree and branch afterward (`discard_changes: true`) — no
   trace left on disk or in git history; `main` was never touched by this exercise.

Result: **rollback is physically proven to work**, not just described in prose.

## 3. Real-data (non-fixture) test — Definition of Done item 8 ("Tests prove live path behavior
against real data, not only fixture behavior")

Added `investment_screener/backend/tests/py_services/test_ta_sweep_real_data_live_path.py`
(committed this same remediation branch, `4455869b`) — read-only against main checkout's real
`intelligence.sqlite`, skips gracefully (`pytest.mark.skipif`) when that gitignored file isn't
present (fresh checkout, CI, or a machine that hasn't run a real sweep yet).

- Verified passing (3/3) when copied to and run at its real path inside the main checkout
  (temporary copy, removed after verification — the committed copy lives only on this
  remediation branch until merged):
  - `test_load_ta_returns_real_technical_sweep_data` — asserts `_load_ta()` returns non-empty
    real data with plausible field shapes.
  - `test_ta_age_hours_returns_real_age` — asserts `_ta_age_hours()` returns a real non-negative
    staleness value.
  - `test_load_latest_ta_sweep_count_matches_load_ta_ticker_count` — asserts internal consistency
    between the two real-data read paths.
- Confirmed skipping correctly (not erroring) when run inside a fresh worktree with no real DB
  present — 3/3 skipped there, as designed.

## 4. Context Bundle Completion Bar

Per the design spec's §4 Producer/Consumer Mapping table, `ta-sweep-results.json` was referenced
by exactly one skill: `technical-analysis-expert`.

- **Before Wave 5B:** 1 stale filename reference (`plugins/tradingview/skills/technical-
  analysis-expert/SKILL.md:78`, "Results auto-saved to
  `investment_screener/backend/data/ta-sweep-results.json`").
- **After Wave 5B (Task 4, already merged):** 0 references — corrected to describe the real
  SQLite/ledger write path. `plugins/tradingview/README.md`'s equivalent comment was corrected
  in the same commit.
- Verified via `grep -rn "ta-sweep-results" plugins/tradingview/skills/technical-analysis-expert/`
  → zero hits.
- Bundle size impact: the referenced file itself was never bundled by this skill (SKILL.md only
  described where results were written, never instructed bundling the raw data file) — the
  measurable reduction is the 1 stale/misleading reference removed, not a byte-count delta.

## 5. Hybrid Exit Criteria (design spec § "Hybrid Exit Criteria")

Per-domain, the three-part test: producer cutover, consumer cutover, archive.

| Test | Status | Evidence |
|---|---|---|
| Producer cutover | **DONE** | `ta_sweep_batch.py::save_sweep_results()` writes SQLite/ledger unconditionally (Task 4, `59e710cc`); confirmed live via §1's real sweep run above. |
| Consumer cutover | **DONE, 3/3** | `compute_conviction_scores.py::_load_ta()`, `daily_brief.py::_ta_age_hours()`, `daily_brief.py::run()`/`_load_latest_ta_sweep_count()` — all SQLite-only, no fallback branch remains reachable (Tasks 2–3). |
| Archive | **DONE** | `git mv` to `ARCHIVE/investment_screener/backend/data/ta-sweep-results.json` (Task 5, `f88b6af8`); confirmed old path no longer resolves; confirmed `ARCHIVE/` copy readable and used for both the rollback exercise (§2) and would be the restore source for any future real rollback. |

No domain is left in dual-write/hybrid state — matches the target architecture ("SQLite/domain
model as authoritative... hybrid operation is a temporary migration aid, never a resting state").

## Outcome

All four skipped items from Wave 5B's original plan are now closed with physical evidence, not
just documentation. Wave 5B (original PR #93 + this remediation) now satisfies the design spec's
actual 9-item Definition of Done and §5 Validation Strategy in full. Map Debt entry updated to
`Status: RESOLVED`.
