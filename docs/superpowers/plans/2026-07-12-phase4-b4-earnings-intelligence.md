# Phase 4, Sub-Spec 2 — B4 Earnings Intelligence Implementation Plan

**Spec:** `docs/superpowers/specs/2026-07-12-phase4-b4-earnings-intelligence-design.md`
**Date:** 2026-07-12
**Approach:** TDD via `superpowers:subagent-driven-development` in a fresh worktree

## Dependency check

- ✅ **E3 (Prediction Ledger)** is merged to main and live
  - `data/predictions.jsonl` exists and is append-only
  - `data/predictions_graded.jsonl` exists and is append-only
  - E3's schema reserves `type: "earnings_expectation"` enum value
- ✅ **Earnings calendar data** already available via `earnings_calendar.py`
- ✅ **`fetch_financials.py`** can provide TTL-cached earnings dates if needed
- ⚠️ **yfinance consensus** may be NULL for newer tickers — graceful degrade required

## Task decomposition (9 TDD tasks)

### Task 1: Schema & constants (foundation)
- [ ] Create `py_services/earnings_expectations.py` with skeleton
- [ ] Define `EarningsExpectation` and `EarningsGrade` Pydantic models
- [ ] Add enum value to E3's prediction type schema (verify round-trip)
- [ ] Test: `test_earnings_expectation_claim_schema_round_trips_jsonl.py`

### Task 2: Consensus fetcher (yfinance integration)
- [ ] Implement `_fetch_consensus_for_ticker(ticker)` helper
- [ ] Graceful NULL handling for missing consensus
- [ ] Handle yfinance API errors (rate limit, timeout) with retry + fallback
- [ ] Test: `test_fetch_consensus_for_ticker_returns_dict_or_none.py`

### Task 3: Harvest core logic (dedup on unchanged consensus)
- [ ] Implement `harvest_earnings_expectations()` main function
- [ ] Read tail of `predictions.jsonl` efficiently (last 1000 lines, filter by ticker+type)
- [ ] Dedup: compare current consensus to last-logged value
- [ ] Append new claim only if consensus changed or no prior record
- [ ] Test: `test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py`

### Task 4: Harvest on consensus change
- [ ] Verify harvest logic appends when consensus updates
- [ ] Handle multi-source scenarios (e.g., estimate revised mid-week)
- [ ] Test: `test_harvest_earnings_expectations_logs_consensus_change.py`

### Task 5: Harvest graceful degrade (NULL consensus)
- [ ] Verify NULL consensus is handled without error
- [ ] No claim logged if consensus unavailable
- [ ] Test: `test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py`

### Task 6: Grade core logic (beat/meet/miss classification)
- [ ] Implement `grade_earnings_expectations()` main function
- [ ] Fetch actual results from yfinance (post-earnings-date only)
- [ ] Classify: BEAT (>1.02x), MEET (±2%), MISS (<0.98x)
- [ ] Append grading records to `predictions_graded.jsonl`
- [ ] Test: `test_grade_earnings_expectations_classifies_beat_meet_miss.py`

### Task 7: Grade structural checks (past-date-only, idempotence)
- [ ] Verify grading only runs on dates <= today
- [ ] Idempotence check: grading the same prediction twice produces identical output
- [ ] Test: `test_grade_earnings_expectations_only_grades_past_dates.py`

### Task 8: Context aggregator for /daily brief
- [ ] Implement `get_earnings_context(ticker, days_ahead=7)`
- [ ] Query `target-portfolio.json` for holdings in earnings window
- [ ] Aggregate: date, consensus, prior beat%, current weight, target action
- [ ] Handle missing history gracefully (first earnings in ledger)
- [ ] Test: `test_get_earnings_context_returns_prior_beat_rate.py`

### Task 9: Integration into /daily and /weekly-review
- [ ] Wire `harvest_earnings_expectations()` into `/daily`'s harvest step (non-blocking)
- [ ] Wire `grade_earnings_expectations()` into `/weekly-review` Phase 2
- [ ] Add "📊 UPCOMING EARNINGS" section to daily brief template
- [ ] Add earnings grades to weekly brief
- [ ] Feed grading output into E3's `generate_track_record_report.py`
- [ ] Test: `test_earnings_expectation_claim_round_trips_ledger.py` (integration)

## Execution strategy

1. **Worktree setup:** `git worktree add .worktrees/feature-fable5-phase4-b4-earnings-intelligence`
2. **Task dispatch order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (sequential, TDD)
   - Tasks 1-2 are foundation (schema, yfinance integration)
   - Tasks 3-5 are harvest logic + variants
   - Tasks 6-7 are grading logic
   - Task 8 is context aggregation (for /daily UI)
   - Task 9 is final integration + whole-branch test
3. **Review gates:**
   - After each task: task-level review (code correctness, test pass)
   - After Task 9: whole-branch review (architecture, integration points, test coverage)
4. **Merge strategy:** Fast-forward to local `main` (expected: no divergence during B4 work)
   - Then push to `origin/main` directly (per git policy)

## Acceptance gates

- [ ] All 9 TDD tasks complete with passing tests
- [ ] `harvest_earnings_expectations()` CLI runs without error on live data
- [ ] `grade_earnings_expectations()` CLI runs without error post-earnings
- [ ] `/daily` brief displays upcoming earnings for ACCUMULATE holdings
- [ ] `/weekly-review` displays past-week earnings grades
- [ ] Track-record report includes earnings_expectation claim counts
- [ ] Whole-branch review returns "Ready to merge"
- [ ] Push to `origin/main`

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| yfinance consensus NULL for many holdings | Graceful degrade in Task 5; no blocking |
| Earnings date conflicts (same ticker, multiple dates, yfinance stale) | Test fixture: define known dates; verify fetch is fresh |
| Grade runs before earnings actually published (timing bug) | Structural check in Task 7: only grade if date <= today |
| Harvest appends duplicate claims on repeated runs | Dedup test in Task 3: verify no duplicates on same consensus |
| Integration with E3 ledger fails silently | Round-trip test in Task 9 |

## Timeline estimate

- Tasks 1-2 (foundation): 30 min
- Tasks 3-5 (harvest + variants): 60 min
- Tasks 6-7 (grading + checks): 45 min
- Task 8 (context): 30 min
- Task 9 (integration + review): 45 min
- **Total (no re-work):** ~3.5 hours
- **With one fix round per 2-3 tasks:** ~4.5 hours

## Post-completion

- Create a follow-up task for `/Predictions.tsx` frontend page (fast-follow, not blocker)
- Monitor earnings ledger for first 2-3 weeks to catch edge cases
- Gather historical beat rates once we have 10+ data points per holding
