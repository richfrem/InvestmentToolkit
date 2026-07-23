# Map Debt Registry

This registry tracks technical debt, process friction, and workarounds.
Entries must be resolved, aged, or escalated. 
Do not delete resolved items; set `Status: RESOLVED` to maintain history.

---

### Entry: test_math_parity.py — PROJECT_ROOT resolves 2 levels short of repo root

- Logged: 2026-07-05
- Cycle/Session: Phase 3 E1 (risk-engine) — discovered during baseline test run before Task 1 dispatch
- Artifact affected: `investment_screener/backend/tests/py_services/test_math_parity.py:6`
- Friction observed: `PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` only walks up 2 directories from `tests/py_services/test_math_parity.py`, landing at `tests/` instead of the repo root. The subsequent `subprocess.run([...os.path.join(PROJECT_ROOT, "investment_screener/backend/py_services/dcf_scenarios.py")...])` call then looks for the script at a doubled, nonexistent path and fails with `No such file or directory`.
- Why it was not fixed now: unrelated to the Phase 3 risk-engine task in progress; fixing it would be an undeclared scope addition mid-task (violates "one logical fix at a time").
- Recommended fix: use `Path(__file__).resolve().parents[4]` (matching the convention already used consistently elsewhere in this test directory, e.g. `test_framework_score.py`, `test_risk_engine.py`) instead of two `os.path.dirname()` calls.
- Evidence: `python3 -m pytest tests/py_services/test_math_parity.py -v` → `Exception: Python math failed`; captured stdout shows `can't open file '.../tests/investment_screener/backend/py_services/dcf_scenarios.py'`.
- Severity: S
- Repeat: NO (isolated to this one file)
- Status: RESOLVED
- Resolution (2026-07-10, Phase 3 E2 session, at explicit user request rather than deferred further): applied the recommended fix verbatim — `PROJECT_ROOT` now computed via `Path(__file__).resolve().parents[4]`, matching every other test file in this directory. `python3 -m pytest tests/py_services/test_math_parity.py -v` → 1 passed.

### Entry: test_place_order_gates.py — 3 tests coupled to real-world weekday/market-hours state

- Logged: 2026-07-05
- Cycle/Session: Phase 3 E1 (risk-engine) — discovered during baseline test run before Task 1 dispatch
- Artifact affected: `investment_screener/backend/tests/py_services/test_place_order_gates.py` — `test_stale_portfolio_exits_4`, `test_fresh_portfolio_exits_0`, `test_size_cap_exits_3`
- Friction observed: these tests invoke the real `place_order.py --preflight` CLI, which checks live NYSE market-hours state before evaluating the gate under test (stale-data, fresh-portfolio, size-cap). When run on a weekend (as today, 2026-07-05 is a Sunday), the market-closed gate fires first and returns exit code 5 with "🚫 Weekend — NYSE is closed" instead of the expected gate-specific exit code (4, 0, 3 respectively) — the tests are not isolated from wall-clock/calendar state.
- Why it was not fixed now: unrelated to the Phase 3 risk-engine task in progress; the real fix (mocking/injecting market-hours state so these gate-order tests are calendar-independent) is a test-harness change outside this task's scope.
- Recommended fix: add a way to override/mock the market-hours check in `place_order.py`'s preflight path (e.g. an env var or `--skip-market-hours-check` test-only flag) so these three tests assert the gate they name regardless of what day they run.
- Evidence: `python3 -m pytest tests/py_services/test_place_order_gates.py -v` on 2026-07-05 (Sunday) → all 3 fail with returncode 5 / "Weekend — NYSE is closed" instead of their expected returncodes.
- Severity: S
- Repeat: YES — will recur every Saturday/Sunday (and likely market holidays) until fixed
- Status: RESOLVED
- Resolution (2026-07-10, Phase 3 E2 session, at explicit user request rather than deferred further): applied the recommended fix — `_check_market_hours()` in `plugins/tradingview/scripts/place_order.py` now reads a `PLACE_ORDER_NOW_OVERRIDE` env var (ISO 8601 UTC timestamp) when set, falling back to `datetime.now(timezone.utc)` when unset (production behavior unchanged — additive only). The 3 named tests plus `test_stale_with_ack_stale_proceeds` (same fragility class, not originally named) now pin a known in-hours weekday timestamp via this override instead of depending on the real wall clock. Added a new dedicated test, `test_market_closed_exits_5_and_ack_closed_bypasses`, asserting the market-hours gate itself (previously zero direct coverage) using a pinned Saturday timestamp, plus `--ack-closed` bypass behavior. `python3 -m pytest tests/py_services/test_place_order_gates.py -v` → 11 passed. Note: the failures observed *this session* before the fix were actually a worktree-only environment gap (`tradingview-cdp/node_modules` never installed here, resolved via `npm ci`), not a live reproduction of the documented market-hours race — the wall-clock-coupling design fix above was applied proactively per the documented recommendation, independent of that day's actual symptom.

### Entry: subagent-driven-development implementer wrote to main checkout instead of worktree (2nd occurrence)

- Logged: 2026-07-09
- Cycle/Session: Phase 3 C2 (market regime classifier) — discovered during final merge prep, `git status` in the main checkout showed an uncommitted, incomplete copy of `daily_brief.py`'s Task 7 changes that should only have existed in the worktree
- Artifact affected: process/workflow — `superpowers:subagent-driven-development` dispatch pattern for this project, not a specific code file
- Friction observed: despite every implementer/fix subagent being explicitly instructed to `cd` into the worktree and confirm via `pwd`/`git branch --show-current` before any edit — and every subagent's report claiming that confirmation passed — a stray, uncommitted, incomplete edit still landed in the main checkout's `plugins/portfolio-advisor/scripts/daily_brief.py` during Task 7's fix rounds. This is the SAME class of incident documented informally in `start_here.md` for Phase 2b's Task 3 (an implementer committed onto the user's active main-checkout branch instead of its worktree) — confirming the existing mitigation (explicit path instruction + pwd/branch confirmation) is insufficient on its own, not a one-off fluke.
- Why it was not fixed inline immediately: not caught until the final pre-merge `git status` check, because no per-task verification of the *main checkout's* cleanliness was happening between tasks — only the worktree's own state was checked during each task's dispatch/review cycle.
- Root cause (best available, not fully forensically confirmed): `cd` inside a Bash tool call only changes that tool's persisted shell state; the Edit/Write/Read tools resolve on the exact absolute path parameter given, independent of any prior `cd`. A `pwd`/`git branch` confirmation via Bash therefore does not guarantee every subsequent Edit/Write call in that same subagent session targets a path under the confirmed directory.
- Fix applied now (not deferred): authored `.agent/rules/worktree-subagent-isolation.md`, a new durable, git-tracked rule mandating `git status --short` in the **main checkout** (not the worktree) after every subagent-driven-development task, before generating the review package — catches a leak within one task cycle, while it's still uncommitted and trivially discardable, instead of only at final-merge time. Referenced (not duplicated) from `.claude/CLAUDE.md` pitfall #28 as a one-line pointer, matching how CLAUDE.md's rule 1 already references `test-driven-development.md` — `.claude/CLAUDE.md` itself is gitignored/local-only, so the rule file is the actual durable, shared fix.
- Evidence: `git diff plugins/portfolio-advisor/scripts/daily_brief.py` in the main checkout (pre-merge, pre-discard) showed a partial version of Task 7's changes — present through the NameError fix commit but missing the later NEUTRAL-restoration and defensive-`.get()` fixes — confirming it was a stray leak from mid-task, not intentional or user-authored work. Discarded safely via `git checkout -- plugins/portfolio-advisor/scripts/daily_brief.py` before merging, since the complete, reviewed version already existed properly committed on the feature branch.
- Severity: M (no data/history damage this time since caught pre-merge and uncommitted, but repeated occurrence across two separate phases is a real reliability gap in the dispatch pattern itself)
- Repeat: YES — 2nd occurrence (1st: Phase 2b Task 3, documented in `start_here.md`, not previously logged here in map-debt.md)
- Status: RESOLVED — preventive process fix (`.agent/rules/worktree-subagent-isolation.md`) applied in this session, not just documented; future occurrences will be caught per-task rather than only at merge time

### Entry: harvest-earnings tests mutate the real, tracked predictions.jsonl instead of a fixture

- Logged: 2026-07-15
- Cycle/Session: Phase 5 whole-branch review + merge/cleanup session — discovered when the Phase 5 worktree showed an uncommitted, duplicated `predictions.jsonl` diff after a fix subagent ran the full `py_services/` suite, then reproduced independently when this session's own post-merge full-suite run on `main` mutated the same tracked file again.
- Artifact affected: `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_*.py` (dedup, consensus-change, null-consensus-degradation test files) and whatever code path in `harvest_predictions.py`/`earnings_expectations.py` they exercise for output-path resolution.
- Friction observed: these tests make a REAL live `yfinance` network call and append a REAL entry to the tracked `investment_screener/backend/data/predictions.jsonl` — not test-isolated to a `tmp_path` fixture like every other data-writing test in this suite. Merely running the full test suite (not even targeting these files specifically) pollutes the live prediction-tracking ledger with non-deliberate entries, and running it multiple times in the same session compounds duplicate/near-duplicate rows under what should be a unique `ticker:type:date` id. Confirmed 3 separate real-network writes to the tracked file across this one session alone (2 caught and reverted from the main checkout; a 3rd, plus the original 2, accumulated uncommitted in the Phase 5 worktree and were discarded during worktree cleanup after content analysis showed no genuinely distinct data — see this session's conversation for the entry-by-entry comparison).
- Why it was not fixed now: root cause not investigated (likely a missing `tmp_path`/monkeypatched output-path fixture in one or more of these test files, or a shared `PREDICTIONS_PATH` constant not overridden the way other test files in this suite already override e.g. `PLACE_ORDER_PORTFOLIO_PATH`) — out of scope for the Phase 5 merge/cleanup this entry was logged during; flagged explicitly by the user as a "not required, worth a dedicated fix" item rather than a blocker.
- Recommended fix: identify the fixture/path-override pattern already used elsewhere in this test directory (e.g. `PLACE_ORDER_PORTFOLIO_PATH` env var override in `test_place_order_gates.py`, or direct `tmp_path`-based monkeypatching in other `py_services` tests) and apply the equivalent to whichever function in `harvest_predictions.py`/`earnings_expectations.py` resolves the real `data/predictions.jsonl` path, so these tests write to an isolated temp file instead.
- Evidence: `git diff investment_screener/backend/data/predictions.jsonl` after running `python3 -m pytest investment_screener/backend/tests/py_services/` (system Python, no path override) showed new `AAPL:earnings_expectation:<today>` entries with real, current `harvestedAt` timestamps and real fetched consensus/price data — not fixture data.
- Severity: S (no data corruption in the sense of wrong values — the appended entries are real, accurate market data — but they're unintentional, duplicate-id pollution of a ledger meant for deliberate daily observations, and will keep recurring on every full-suite run until fixed)
- Repeat: YES — reproduced independently 3 times in this single session already; will recur for any future contributor who runs the full suite
- Status: RESOLVED — root cause was exactly as predicted: `harvest_earnings_expectations()` had no path-override parameter. Added `predictions_path: Path = PREDICTIONS_PATH` (imported from `prediction_ledger.py`), threaded to both `_load_predictions(predictions_path)` and `_append_prediction(record, predictions_path)`. Updated all 3 existing test files (dedup/consensus-change/null-consensus) plus a new `test_harvest_earnings_expectations_path_isolation.py` to pass a `tmp_path`-based override on every call. The specific culprit test (`test_harvest_missing_predictions_file_returns_empty`) had zero mocks for `_fetch_consensus_for_ticker`/`_append_prediction`, so it silently fell through to a real network call + real write; it now also has the missing mocks as defense-in-depth. Verified via `git diff --stat data/predictions.jsonl` showing zero change after running the full 4-file suite (20/22 tests passing — see new entry below for the 2 that failed for unrelated reasons).

---

### Entry: two harvest_earnings_expectations tests fail on genuine logic mismatches, unmasked by fixing an unrelated mock-variable typo

- Logged: 2026-07-17
- Cycle/Session: Consolidation & trust fixes (Task 5) — discovered while fixing the predictions.jsonl test-isolation bug above. While rewriting the 3 harvest test files to add `predictions_path`, found that 9 of 12 originally-"failing" tests were actually failing due to an unrelated bug: `patch("earnings_expectations.date") as mock_date_class` bound one name but the test body referenced the never-defined `mock_date`, raising a `NameError` before `harvest_earnings_expectations()` was ever called. Fixed the reference (mechanical rename, zero production-code impact) as a low-risk byproduct of touching every one of these lines. That unmasked 2 tests that now run to completion but fail for real, pre-existing reasons unrelated to path isolation.
- Artifact affected: `investment_screener/backend/py_services/earnings_expectations.py` (`EarningsExpectationClaim` model, `harvest_earnings_expectations()`'s yfinance-exception handling) and `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py`.
- Friction observed:
  1. `test_harvest_skips_null_consensus_revenue` expects a claim to still be logged when `consensus_revenue` is `None` (per the code's own docstring: "revenue can be missing"), but `EarningsExpectationClaim.consensus_revenue` is declared as a required `float = Field(...)`, not `Optional[float]`. Passing `None` raises a Pydantic `ValidationError`, silently swallowed by the per-ticker `except Exception: continue`, so `_append_prediction` is never called and the test's `assert_called_once()` fails with "Called 0 times."
  2. `test_harvest_silently_degrades_on_yfinance_exception` expects that a `yf.Ticker()` exception during price fetch means NO claim gets appended, but the actual code catches that exception locally (`except Exception: base_price = 0.0`) and continues to append with a 0.0 fallback price. The test's expectation doesn't match the implemented graceful-degrade design.
- Why it was not fixed now: both are genuine implementation-vs-test disagreements requiring a design decision (should revenue really be optional in the schema? should a price-fetch failure abort the whole claim or degrade to 0.0?) — out of scope for Task 5, which was specifically about ledger-file test isolation, not model/logic correctness.
- Recommended fix: for (1), decide whether `consensus_revenue` should be `Optional[float] = None` in the Pydantic model (matching the docstring's stated intent) or whether the test's expectation is wrong and revenue should in fact be required; for (2), decide whether a price-fetch exception should skip the ticker entirely (matching the test) or keep the current 0.0-fallback degrade (matching the code) and fix the test's expectation to match.
- Evidence: `python3 -m pytest investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py -v` — full tracebacks captured showing `AssertionError: Expected '_append_prediction' to have been called once. Called 0 times.` for (1) and `Called 1 times` (expected 0) for (2).
- Severity: S (test-only correctness gap; no data corruption, no production code path affected beyond the documented degrade behavior)
- Repeat: NO (isolated to these 2 specific test cases)
- Status: OPEN — flagged during Task 5, deferred as a dedicated follow-up per the same "not required, worth a dedicated fix" pattern as the entry above

### Entry: verify_thesis_sync.py requires thesis-doc mention for pure watchlist candidates

- Logged: 2026-07-21
- Cycle/Session: Domain Data Model v3.2 Wave 3 (account holdings) — discovered while committing an
  unrelated real-sync side effect during Task 7's live parity proof, when the pre-commit hook
  blocked the commit.
- Artifact affected: `investment_screener/backend/py_services/verify_thesis_sync.py`'s
  `_load_holdings_from_db()` (calls `list_investments(conn)` with no filter) and its
  "tickers missing in thesis documentation" check.
- Friction observed: the check requires EVERY row in the `investment` table — including pure
  watchlist candidates (`is_watchlisted=1`, `target_weight=NULL`, never actually held or targeted)
  — to be mentioned by name in `investment_thesis.md`/sub-strategy markdown files. ~17 real
  watchlist tickers (AAPL, ALAB, AMZN, BW, CAKE, CELH, CIFR, HUT, KRC, LBRT, NKE, PUMP, RIOT, SEI,
  SYM, TSEM, plus BITF/ANET/EQIX/DLR.U.TO/DLR.TO variants) are real, user-confirmed watchlist
  entries the user hasn't written thesis prose for yet — not phantom/stale data, confirmed via
  `is_watchlisted=1` in `domain_model.sqlite`. The hook currently treats "not yet researched
  watchlist candidate" identically to "real holding/target with no thesis," blocking any commit
  that touches `investment_thesis.md`/sub-strategy files until every watchlist ticker ever added
  gets a real write-up.
- Why it was not fixed now: user explicitly decided the check's current behavior (require
  documentation for every tracked ticker including watchlist) is correct and intends to write the
  missing ~17 real watchlist entries themselves — this is real investment-research content only the
  user can produce accurately, not something to fix by loosening the check or writing placeholder
  content. Also out of Wave 3's scope (Wave 3 is the account-holdings/portfolio.json migration; this
  check concerns `target-portfolio.json`/thesis docs, Wave 2's domain).
- Recommended fix: none — this is the user's own content backlog, not a code fix. If it recurs as
  blocking friction, consider whether `_load_holdings_from_db()` should accept an optional
  `include_watchlist_only` param so future automated commits (e.g. broker-sync side effects) aren't
  blocked on this specific content gap while a real fix (or the user's write-up) is pending —
  named as an option, not a recommendation, since the user's stated preference is to keep the check
  strict.
- Evidence: `python3 verify_thesis_sync.py` (both in the Wave 3 worktree and on `main` independently)
  → `ERROR: The following tickers exist in target portfolio but are missing in thesis documentation:
  [...]`; `SELECT symbol, is_watchlisted, target_weight FROM investment WHERE symbol IN (...)` confirms
  `is_watchlisted=1, target_weight=NULL` for the named tickers.
- Severity: M
- Repeat: YES — will recur on any future commit touching `investment_thesis.md`/sub-strategy files
  until the user writes the missing watchlist entries.
- Status: OPEN

---

### Entry: Wave 4 real migration write ran against the worktree's DB, not main's live DB

- Logged: 2026-07-22
- Cycle/Session: Domain Data Model v3.2 Wave 4 (portfolio operations) — post-merge worktree cleanup
- Artifact affected: `docs/superpowers/plans/2026-07-22-domain-data-model-v3-wave4-implementation-plan.md`
  Task 7 (real migration write), and the wave's controller process generally (this session, and the
  background subagent it dispatched).
- Friction observed: the background subagent controlling Wave 4's Task 7 ran
  `migrate_wave4_to_sqlite.py --write` inside the wave's git worktree
  (`.claude/worktrees/wave4-portfolio-ops`), against that worktree's own copy of
  `investment_screener/backend/data/domain_model.sqlite`. It then verified row counts with a direct
  SQL query and reported success — correctly, for that file. But `domain_model.sqlite` (like
  `portfolio.json`, `cash_flows.json`, and the other JSON sources) is gitignored, so it is **not**
  shared between a worktree and the main checkout — each has its own separate copy on disk that git
  never syncs. After PR #91 merged the code cutover (trading.ts/order_risk_gates.py/
  execution_quality_scorecard.py/ytd_return.py now read exclusively from SQLite) to `main`, the
  session controller (me) did not independently re-check that `main`'s own live
  `domain_model.sqlite` actually contained the migrated rows before treating the wave as complete —
  the gap was caught only because the user asked to clean up the merged worktree, not by any step in
  the wave's own verification or exit-report process. Root cause: I applied the
  gitignored-private-data-doesn't-sync rule correctly for the *archive* step (local-only `mv` for
  `cash_flows.json`) but failed to apply the same reasoning to the *migration write* step for
  `domain_model.sqlite`, and neither the plan nor the dispatched subagent's brief explicitly named
  which checkout the real write and its verification needed to target.
- Why it was not deferred: small, safe, inside allowed edit boundaries (data write only, no schema
  change, fully idempotent via the migration script's content-hash IDs) — fixed immediately per
  policy rule 7 (fix forward, don't defer for later).
- Fix applied: re-ran `migrate_wave4_to_sqlite.py --write` directly against the main checkout's real
  `investment_screener/backend/data/{trade-log.json,orders_executed.jsonl,cash_flows.json}` and real
  `investment_screener/backend/data/domain_model.sqlite`, using explicit `--trade-log`/
  `--orders-executed`/`--cash-flows`/`--db-path` flags (the script's relative-path defaults assume
  being run from `py_services/` against a sibling `../data/`, which does not disambiguate worktree
  vs. main on its own). Verified independently via direct `sqlite3` queries against the main
  checkout's file post-write. Also updated
  `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`'s Global
  Constraints (binding on every wave) to require the real write and its verification explicitly
  target the main checkout, so Waves 5A–5E don't repeat this.
- Evidence: before fix — `sqlite3 investment_screener/backend/data/domain_model.sqlite "SELECT
  COUNT(*) FROM trade_log_entry;"` on `main` → `0`, despite PR #91 (Wave 4) already merged and its
  own report claiming the real write was verified. After fix — same query → `52`; `order_execution`
  → `8`; `cash_flow` → `3`; `cash_flow_baseline` → `ALL|37426.0|2026-01-01`. Dry-run counts against
  `main`'s real source files matched the worktree's original dry-run report exactly (52/8/3, zero
  warnings) before the write ran, confirming no data drift between the two copies' *source* JSON
  (only the derived SQLite state had diverged).
- Severity: L (real data loss risk was low — original JSON source files were never touched or
  deleted, so nothing was unrecoverable — but the live app would have silently shown empty
  Trade Log / YTD Return data on next backend restart had this gone unnoticed)
- Repeat: YES until the Global Constraints fix above is followed by every future wave's real-write
  task — flagged there specifically so it's read before each wave's Task 7-equivalent runs.
- Status: RESOLVED

### Entry: Wave 5B — plan omitted the spec's real Validation Strategy and Definition of Done, self-invented a narrower bar

- Logged: 2026-07-22
- Cycle/Session: Wave 5B (TA Sweep Results) post-merge closeout — discovered when the user asked
  "shouldn't observations.jsonl be events in the SQLite model" then explicitly said "you are
  missing the whole point of these waves. review the main plan again."
- Artifact affected: `docs/superpowers/plans/2026-07-22-wave5b-ta-sweep-results.md` (the wave-level
  plan document), and by extension every task/final-branch code review dispatched against it,
  since none were ever asked to check for the missing items — they correctly reviewed against the
  narrower bar the plan gave them.
- Friction observed: the overall migration plan (`docs/superpowers/plans/2026-07-19-...md`)
  requires every wave plan to include five specific sections (Hybrid Exit Criteria, Wave KPI
  table, **Context Bundle Completion Bar**, Producer/Consumer cutover table, Archive/retention
  decision) plus satisfy the design spec's §5 Validation Strategy (schema/migration/repository/
  consumer/**parity-over-a-real-live-cycle**/live-path/grep-scan/archive/**physically-exercised
  rollback**/context-bundle tests) and its 9-item Definition of Done (item 8: "tests prove live
  path behavior against real data, not only fixture behavior"). Wave 5B's plan invented its own
  5-item "Definition of Done" instead of copying these verbatim, silently dropping: the
  parity-over-a-real-cycle diff, the physically-exercised rollback, the real-data (non-fixture)
  test, the Context Bundle Completion Bar measurement, and the Hybrid Exit Criteria section. All
  6 task-level reviews and the final whole-branch review came back clean because they were scoped
  to code-diff quality against the plan as written, not against the spec's actual required bar —
  the gap was in what the plan asked reviewers to check, not in how carefully they checked it.
- Why it was not fixed before merge: not caught — the plan's self-review step (writing-plans
  skill's "Spec coverage" self-check) was run against the plan's own text, not cross-checked
  against the design spec's §5/Definition-of-Done sections as an independent source of truth.
- Recommended fix (applied same session): added a new Global Constraint to the overall plan
  requiring every wave plan to paste the spec's full §5 checklist and 9-item Definition of Done
  verbatim (not a self-invented subset), and hardened the reusable kickoff-prompt "Way of Working"
  template (`docs/superpowers/status/wave5b-kickoff-prompt.md`, copied forward to each new wave's
  kickoff prompt) to name this explicitly in its "Plan the wave" step.
- Evidence: `grep -n "Validation Strategy\|Definition of Done" docs/superpowers/plans/2026-07-22-wave5b-ta-sweep-results.md`
  → zero hits for the spec's actual section names; the plan's own "Definition of Done for This
  Wave" section had 5 items, none matching the spec's 9.
- Severity: M — no data was lost or corrupted (the real migration write itself was independently
  verified correct), but the wave was declared complete and merged without the validation gates
  the spec exists specifically to enforce, on a domain whose own history (ADR-029) is literally
  about a wave being falsely certified complete this same way.
- Repeat: YES until the Global Constraints fix above is followed by every future wave's plan —
  flagged there specifically so it's read before each wave's `superpowers:writing-plans` pass.
- Status: OPEN (remediation for Wave 5B itself — real-cycle parity test, rollback exercise,
  real-data test, Context Bundle number — in progress this same session)
