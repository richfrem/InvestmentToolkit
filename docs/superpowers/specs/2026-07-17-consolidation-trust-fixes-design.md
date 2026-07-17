# Consolidation & Trust — 5 Verified Fixes — Design

_Date: 2026-07-17_

## Context

After Phase 6 shipped, an external review ("Fable," the same reviewer who authored the original
elevation guide) was run against a bundle of Phase 6 specs/plans, then a targeted follow-up bundle
of specific files. The review produced concrete, falsifiable claims; each was independently
verified against the actual repo before being accepted (not taken on faith) — four claims via
direct `find`/`grep` checks, three more via reading the actual named files in full. This spec
covers the resulting task list: five small, independent, verification-backed fixes, explicitly
scoped by Fable as "no design work required."

## Scope — 5 fixes

### 1. Cache-key collision (`investment_screener/backend/py_services/market_data.py`)
`get_estimates()` and `get_fundamentals()` both call `cache_get`/`cache_set` with the identical key
pair `(ticker, "fundamentals")`. Whichever runs second for a given ticker overwrites the other's
cache entry — any caller that needs both (e.g. a full `/evaluate-stock` pass, since DCF needs
estimates while comps/wacc need fundamentals) silently loses caching and refetches. Fix:
`get_estimates()` uses its own key, `"estimates"`, instead.

### 2. Converged-flag bug (`plugins/stock-valuation/scripts/reverse_dcf.py`)
`solve_implied_growth()`'s bisection loop can exit via `MAX_ITERATIONS` exhaustion without ever
satisfying the tolerance check (`converged` stays `False`), but the function's final return block
unconditionally computes and returns `impliedGrowth`, `impliedGrowthVsBaseCase`, and
`impliedGrowthVsGuidance` regardless of `converged`'s value — only the separate `OUT_OF_BRACKET_RANGE`
early-return path correctly nulls these fields. `validate_projection.py`'s `check_accumulate_gate()`
consumes `impliedGrowthVsBaseCase` via an `is not None` check, so a non-converged-but-numeric value
can silently supply one of the two lenses ACCUMULATE needs. Severity note (confirmed during
research, and acknowledged by the reviewer): with a 550pp bracket and 200 iterations on a monotonic
PV function, iteration-exhausted non-convergence is practically unreachable — this is a latent
invariant violation, not an observed live risk. Still worth fixing because it's cheap and the gate
is load-bearing. Fix: null all three fields when `converged` is `False`, mirroring the
`OUT_OF_BRACKET_RANGE` pattern already in the same function. No change needed in
`validate_projection.py` — its existing `is not None` check already does the right thing once the
null is real.

### 3. `cik` threading (`plugins/stock-valuation/scripts/comps_valuation.py`)
`_peer_ev_sales()` and `comps_implied_range()` call `get_fundamentals(ticker)` with no `cik`
argument, so `_safe_edgar_facts()` always receives `None` and EDGAR is structurally always skipped
— `comps`'s `dataQuality.conflicts` is therefore always empty, and the cross-source-conflict HALT
path (`data-quality-agent`'s documented decision tree) is effectively wacc-only today. **Refined
scope, post-research**: there is no ticker→CIK lookup service anywhere in this repo, and the CIK
used by the `13f-tracker` skill is a 13F *filer's* (fund's) CIK, not reusable for looking up an
arbitrary company's own EDGAR facts — Fable's suggestion to reuse the 13F CIK map doesn't actually
apply. The real established pattern for this, already used identically by `wacc.py` and
`framework_score.py`, is an optional `--cik` CLI flag supplied by the caller for the *target*
ticker only. Fix: add the same optional `cik` parameter to `comps_valuation.py`, threaded to
`get_fundamentals(ticker, cik=cik)` for the target ticker. **Peer-level CIK threading is explicitly
out of scope** — there's no per-peer CIK source, and building one (a real ticker→CIK resolution
service) is a separate, larger feature, not part of this fix.

### 4. `.pylock` files tracked in git
Investigation found this is **not a lock-release bug** — `file_lock.py`'s POSIX path creates a
sentinel file (`path.pylock`) via `.touch(exist_ok=True)` and never deletes it; `fcntl.flock(LOCK_UN)`
releases the OS-level advisory lock but intentionally leaves the sentinel file in place, which is
the correct, standard pattern for `fcntl`-based file locking (the file is a lock handle, not lock
content — deleting it would risk races with concurrent acquisition). The actual issue: 7 of these
empty sentinel files (`BE`, `CORZ`, `CRWV`, `IREN`, `NBIS`, `PANW`, `RKLB` — confirmed via
`git ls-files`) are tracked in git despite `.gitignore` already having a `*.pylock` rule (line 110)
— they were added before that rule existed and never untracked afterward. Fix: `git rm --cached`
those 7 files (remain on disk locally, stop being tracked/committed going forward).

### 5. `predictions.jsonl` test isolation (`.agent/map-debt.md`, "harvest-earnings tests mutate the
real, tracked predictions.jsonl instead of a fixture", Status: OPEN)
Root cause confirmed: `earnings_expectations.py`'s `harvest_earnings_expectations(tickers)` has **no
path-override parameter at all** — unlike `harvest_predictions.py`'s functions, which already
correctly accept a `predictions_path: Path = PREDICTIONS_PATH` parameter for exactly this purpose.
The three test files (`test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py`,
`test_harvest_earnings_expectations_logs_consensus_change.py`,
`test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py`) call
`harvest_earnings_expectations(["AAPL"])` with no way to inject an isolated path, so every run
appends real entries (with a real live `yfinance` network call) to the actual tracked
`data/predictions.jsonl`. Fix: add `predictions_path: Path = PREDICTIONS_PATH` to
`harvest_earnings_expectations()`'s signature, thread it through internally, and update all three
test files to pass a `tmp_path`-based override — matching `test_generate_track_record_report.py`'s
and `harvest_predictions.py`'s own existing isolation pattern.

## Verification

Each fix gets its own failing-test-first regression test (TDD, per this repo's standing rule),
plus a run of the existing test suite for that file/module to confirm no regressions. Fix 4 (the
`.pylock` untracking) has no code test — verification is `git status`/`git ls-files` showing the 7
files no longer tracked, and a smoke-run of any script that calls `locked_write_json()` to confirm
locking still works with the files present on disk but untracked.

## Out of Scope

- Peer-level CIK threading for `comps_valuation.py` (no CIK source exists for peers).
- Building a ticker→CIK resolution service.
- Any broader "13F pair" or "portfolio-health vs strategic-review" consolidation — the reviewer
  downgraded the 13F claim to "optional, low priority" after reading the actual files, and
  portfolio-health/strategic-review wasn't part of this review's file set at all.
- The eval runner (`run_skill_evals.py`) and the yfinance/cache-system consolidation — both real,
  both larger, both queued as separate future work per Fable's own Q4 priority list.
