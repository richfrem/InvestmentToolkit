# Consolidation & Trust — 5 Verified Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans in a real git worktree (`superpowers:using-git-worktrees`) — these are real code changes, worktree is mandatory per `.agent/rules/git-operations.md`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 small, independent, externally-reviewed-and-verified issues: a cache-key collision,
a DCF converged-flag bug, missing `cik` threading in comps, 7 stale tracked `.pylock` files, and a
test-isolation bug that pollutes the real `predictions.jsonl`.

**Architecture:** Five independent, small patches across `py_services/` and `plugins/stock-valuation/scripts/`,
each with its own regression test. No shared interfaces between the five — they can be done in any
order.

**Tech Stack:** Python 3.11, pytest.

## Global Constraints

- Full spec: `docs/superpowers/specs/2026-07-17-consolidation-trust-fixes-design.md`.
- Real git worktree required (this is code, not docs) — create via `superpowers:using-git-worktrees`
  before starting Task 1.
- Direct implementation (no subagent dispatch) — confirmed with the user given the small,
  well-understood scope of each fix.
- Peer-level CIK threading in `comps_valuation.py` is explicitly out of scope for Task 3.
- Never touch the real gitignored `data/predictions.jsonl` from a test — Task 5's tests must use
  `tmp_path` fixtures exclusively.
- Sequence at the end: whole-branch review → merge worktree branch into local `main` → push `main`
  to `origin/main`.

---

### Task 1: Cache-key collision in `market_data.py`

**Files:**
- Modify: `investment_screener/backend/py_services/market_data.py`
- Modify: `investment_screener/backend/tests/py_services/test_market_data.py` (or create if it
  doesn't already cover this — check first)

- [ ] **Step 1: Check for an existing test file covering `get_estimates`/`get_fundamentals` caching**
  ```bash
  grep -rln "get_estimates\|get_fundamentals" investment_screener/backend/tests/py_services/*.py
  ```
  Use whichever file already covers these functions; only create a new one if none exists.

- [ ] **Step 2: Write the failing test** — assert that calling `get_fundamentals(ticker)` after
  `get_estimates(ticker)` (both hitting the cache) does not clobber the fundamentals cache entry:
  ```python
  def test_get_estimates_and_get_fundamentals_do_not_share_cache_key(tmp_path, monkeypatch):
      # Point CACHE_DIR (or however market_data.py resolves its cache location) at tmp_path
      # Call get_estimates(ticker) first (mocking yfinance as needed), then get_fundamentals(ticker)
      # Assert cache_get(ticker, "estimates") and cache_get(ticker, "fundamentals") are both
      # populated and distinct — neither overwrote the other.
  ```
  (Read `market_data.py`'s actual cache module/functions first to write this against the real
  mocking seams already used by its existing tests — don't invent a different cache-access pattern.)

- [ ] **Step 3: Run to verify it fails**
  ```bash
  cd investment_screener/backend && python3 -m pytest tests/py_services/test_market_data.py -k cache -v
  ```
  Expected: FAIL — both keys currently resolve to the same cache slot.

- [ ] **Step 4: Fix** — in `market_data.py`, change `get_estimates()`'s `cache_get(ticker, "fundamentals")`
  (line ~268) and `cache_set(ticker, "fundamentals", entry)` (line ~287) to use `"estimates"` instead.

- [ ] **Step 5: Run to verify it passes**, then run the full `market_data.py` test file to confirm
  no regressions:
  ```bash
  python3 -m pytest tests/py_services/test_market_data.py -v
  ```

- [ ] **Step 6: Commit** (inside the worktree)
  ```bash
  git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data.py
  git commit -m "fix: give get_estimates() its own cache key, was colliding with get_fundamentals()"
  ```

---

### Task 2: Converged-flag bug in `reverse_dcf.py`

**Files:**
- Modify: `plugins/stock-valuation/scripts/reverse_dcf.py`
- Modify or create: a test file covering `solve_implied_growth` (check
  `plugins/stock-valuation/tests/` or wherever this plugin's tests live first)

- [ ] **Step 1: Locate existing tests**
  ```bash
  find plugins/stock-valuation -iname "*reverse_dcf*" -path "*test*"
  ```

- [ ] **Step 2: Write the failing test** — force a non-convergent bisection (e.g. mock/construct
  inputs where `MAX_ITERATIONS` is reached without satisfying `tolerance`, or directly unit-test
  the post-loop branch) and assert `impliedGrowth`, `impliedGrowthVsBaseCase`, and
  `impliedGrowthVsGuidance` are all `None` when `converged` is `False`:
  ```python
  def test_solve_implied_growth_nulls_fields_when_not_converged(monkeypatch):
      # Patch MAX_ITERATIONS very low (e.g. 1) and/or RELATIVE_TOLERANCE impossibly tight so the
      # loop exhausts without converging, for inputs that are inside the bracket (not OUT_OF_BRACKET_RANGE).
      result = solve_implied_growth(...)
      assert result["converged"] is False
      assert result["impliedGrowth"] is None
      assert result["impliedGrowthVsBaseCase"] is None
      assert result["impliedGrowthVsGuidance"] is None
  ```

- [ ] **Step 3: Run to verify it fails**
  ```bash
  python3 -m pytest <test_file> -k not_converged -v
  ```

- [ ] **Step 4: Fix** — in `solve_implied_growth()`'s final return block, null the three fields
  when `converged` is `False`, mirroring the `OUT_OF_BRACKET_RANGE` early-return's pattern. Keep
  `verdict` computable (or set it to a sentinel like `"NON_CONVERGENT"` — check what
  `validate_projection.py` and any other consumer expects for `verdict` before deciding; the spec
  only requires nulling the three growth fields).

- [ ] **Step 5: Run to verify it passes**, then run the full `reverse_dcf.py` test suite.

- [ ] **Step 6: Confirm `validate_projection.py`'s `check_accumulate_gate()` needs no change** —
  its `implied_growth_lens` already checks `implied_growth_vs_base is not None`, so once the field
  is genuinely `None` on non-convergence, this self-corrects. Add one regression test in
  `validate_projection`'s own test file confirming a non-converged reverseDcf result correctly
  fails the `impliedGrowth` lens (not just that `reverse_dcf.py` nulls it).

- [ ] **Step 7: Commit**
  ```bash
  git add plugins/stock-valuation/scripts/reverse_dcf.py <test files>
  git commit -m "fix: null implied-growth fields in reverse_dcf.py when bisection doesn't converge"
  ```

---

### Task 3: `cik` threading in `comps_valuation.py` (target ticker only)

**Files:**
- Modify: `plugins/stock-valuation/scripts/comps_valuation.py`
- Modify or create: its test file

- [ ] **Step 1: Read `wacc.py`'s existing `--cik` CLI pattern** (the established sibling
  convention) before touching `comps_valuation.py` — match its parameter naming and argparse flag
  exactly, don't invent a different convention.

- [ ] **Step 2: Write the failing test** — assert that passing `cik=` to `comps_implied_range()`
  (or `_peer_ev_sales()`, whichever is the more natural injection point for the target ticker)
  results in `get_fundamentals()` being called with that `cik` for the target ticker (mock
  `get_fundamentals` and assert its call args), while peer calls remain `cik=None` (unchanged,
  confirming peer-level threading is deliberately out of scope):
  ```python
  def test_comps_implied_range_threads_cik_for_target_ticker_only(monkeypatch):
      calls = []
      monkeypatch.setattr(comps_valuation, "get_fundamentals", lambda ticker, cik=None: calls.append((ticker, cik)) or {...})
      comps_valuation.comps_implied_range("NVDA", ["AMD", "AVGO"], projections_dir, cik="0001045810")
      assert ("NVDA", "0001045810") in calls
      assert all(cik is None for (t, cik) in calls if t != "NVDA")
  ```

- [ ] **Step 3: Run to verify it fails**

- [ ] **Step 4: Fix** — add `cik: str | None = None` parameter to `_peer_ev_sales()` and
  `comps_implied_range()`, thread it to the target ticker's `get_fundamentals(ticker, cik=cik)`
  call only (peer calls stay `get_fundamentals(peer)`, unchanged). Add the matching `--cik`
  argparse flag to `main()`, passed through the same way `wacc.py`'s `main()` does it.

- [ ] **Step 5: Run to verify it passes**, then run the full `comps_valuation.py` test suite.

- [ ] **Step 6: Commit**
  ```bash
  git add plugins/stock-valuation/scripts/comps_valuation.py <test files>
  git commit -m "fix: thread optional cik through comps_valuation.py for the target ticker (peer-level threading out of scope)"
  ```

---

### Task 4: Untrack the 7 stale `.pylock` files

**Files:**
- No content changes — a `git rm --cached` operation only.

- [ ] **Step 1: Confirm the exact 7 tracked files and that they're empty (sentinel-only)**
  ```bash
  git ls-files investment_screener/backend/data/projections/*.pylock
  for f in $(git ls-files investment_screener/backend/data/projections/*.pylock); do
    wc -c "$f"
  done
  ```
  Expected: 7 files, all 0 bytes. If any is non-zero, stop and investigate before untracking —
  that would mean it's not a pure sentinel file and something unexpected wrote real content to it.

- [ ] **Step 2: Untrack (keep on disk)**
  ```bash
  git rm --cached investment_screener/backend/data/projections/BE.json.pylock \
                   investment_screener/backend/data/projections/CORZ.json.pylock \
                   investment_screener/backend/data/projections/CRWV.json.pylock \
                   investment_screener/backend/data/projections/IREN.json.pylock \
                   investment_screener/backend/data/projections/NBIS.json.pylock \
                   investment_screener/backend/data/projections/PANW.json.pylock \
                   investment_screener/backend/data/projections/RKLB.json.pylock
  ```

- [ ] **Step 3: Verify** — confirm the files still exist on disk (untouched) and are no longer
  tracked:
  ```bash
  ls investment_screener/backend/data/projections/*.pylock   # should still list all files present locally (10, or however many exist at run time)
  git ls-files investment_screener/backend/data/projections/*.pylock   # should now print nothing
  git status --short | grep pylock   # should show the 7 as staged deletions from git's index only
  ```

- [ ] **Step 4: Smoke-test that locking still works** with the files present but untracked:
  ```bash
  python3 -c "
  from pathlib import Path
  import sys
  sys.path.insert(0, 'investment_screener/backend/py_services')
  from file_lock import locked_write_json
  test_path = Path('/tmp/pylock_smoke_test.json')
  locked_write_json(test_path, {'ok': True})
  print('lock + write succeeded:', test_path.read_text())
  test_path.unlink()
  test_path.with_suffix('.json.pylock').unlink(missing_ok=True)
  "
  ```
  Expected: prints the written content with no errors — confirms untracking didn't touch
  `file_lock.py`'s runtime behavior at all (it never depended on git tracking status).

- [ ] **Step 5: Commit**
  ```bash
  git commit -m "chore: untrack 7 stale .pylock sentinel files (predate the *.pylock gitignore rule)"
  ```

---

### Task 5: `predictions.jsonl` test isolation fix

**Files:**
- Modify: `investment_screener/backend/py_services/earnings_expectations.py`
- Modify: `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py`
- Modify: `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py`
- Modify: `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py`

- [ ] **Step 1: Read `harvest_predictions.py`'s existing `predictions_path: Path = PREDICTIONS_PATH`
  pattern** (the correct sibling convention to mirror) before editing `earnings_expectations.py`.

- [ ] **Step 2: Add the parameter** — change `harvest_earnings_expectations()`'s signature from
  `(tickers: list[str] | None = None)` to `(tickers: list[str] | None = None, predictions_path: Path
  = PREDICTIONS_PATH)`, and thread it through to every internal read/write of the predictions
  ledger inside that function (read the function body fully first to find every such call site —
  don't assume there's only one).

- [ ] **Step 3: Update all three test files** to pass `predictions_path=tmp_path / "predictions.jsonl"`
  (or equivalent) in every call to `harvest_earnings_expectations(...)`, instead of relying on the
  module-level default.

- [ ] **Step 4: Verify test isolation directly** — run the full three test files, then check the
  real tracked file is untouched:
  ```bash
  cd investment_screener/backend
  git diff --stat data/predictions.jsonl   # capture before-state, should be empty
  python3 -m pytest tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py \
                    tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py \
                    tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py -v
  git diff --stat data/predictions.jsonl   # must still be empty after the run — this is the actual fix verification
  ```
  Expected: all tests pass, AND `git diff --stat data/predictions.jsonl` shows no change before or
  after — this is the definitive proof the isolation bug is fixed (a passing test suite alone
  doesn't prove this; the real-file diff check does).

- [ ] **Step 5: Commit**
  ```bash
  git add investment_screener/backend/py_services/earnings_expectations.py \
          investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_*.py
  git commit -m "fix: add predictions_path override to harvest_earnings_expectations(), isolate its 3 tests from the real ledger"
  ```

---

### Final: Whole-branch review, merge, push

- [ ] **Step 1: Run the full backend test suite** in the worktree, confirm no new failures beyond
  the documented pre-existing baseline.
- [ ] **Step 2: Whole-branch review** — dispatch a code-reviewer (per
  `superpowers:requesting-code-review`) against the full worktree diff before merging.
- [ ] **Step 3: Merge the worktree's branch into local `main`**, then push `main` to `origin/main`.
- [ ] **Step 4: Update `.agent/map-debt.md`** — mark the "harvest-earnings tests mutate the real,
  tracked predictions.jsonl instead of a fixture" entry as `Status: RESOLVED`.
