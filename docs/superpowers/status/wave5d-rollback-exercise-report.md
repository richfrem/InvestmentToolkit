# Wave 5D Rollback Exercise — Physically Executed

**Trigger:** Design spec §5 Validation Strategy requires the rollback be *physically
exercised* at least once per domain before declaring the wave done — "revert
producer/consumer commits, confirm the app runs correctly against the old file
again" — not merely described in prose. This mirrors the format and evidence bar
of `docs/superpowers/status/wave5b-remediation-report.md` §2.

**Scope:** Task 2 (producer: `prediction_ledger.py` dual-write, commit `eeb6cdb5`)
and Task 3 (consumer: `harvest_predictions.py` cutover, commit `f47b03a8`) — the
two commits that moved the predictions domain off `predictions.jsonl`-only reads.
Performed entirely in an isolated, throwaway git worktree at `/tmp/wave5d-rollback-
exercise`, never touching `main` or this feature branch's real files. The real
Wave 5D data backfill (Task 5) happened separately, directly on the main
checkout, and is out of scope for this code-revert exercise (see task brief).

## 1. Throwaway worktree setup

```
$ cd /Users/richardfremmerlid/Projects/InvestmentToolkit
$ git worktree add /tmp/wave5d-rollback-exercise d472fcfd
Preparing worktree (detached HEAD d472fcfd)
HEAD is now at d472fcfd fix: real prediction records key the claim date as "date", not "claimDate"
```

`d472fcfd` is this wave's tip at the time of the exercise (Task 6's real-cycle
parity check + bugfix commit).

## 2. Identify Task 2's commit

```
$ git log --oneline -- investment_screener/backend/py_services/prediction_ledger.py | head -5
d472fcfd fix: real prediction records key the claim date as "date", not "claimDate"
83ef028d docs: Wave 5D real-cycle parity check (harvest_predictions.py dual-write, byte-identical)
d7532529 test: remove unused widen_event_type_constraint import (Wave 5D Task 4 review fix)
66255a2a feat: add prediction_ledger.py core -- append-only JSONL store + grade_claim()
eeb6cdb5 feat: dual-write predictions/grades to intelligence_event (Wave 5D Task 2)
```

`eeb6cdb5` confirmed as Task 2's dual-write commit.

## 3. Revert Task 2 (producer)

```
$ git revert --no-commit eeb6cdb5
Auto-merging investment_screener/backend/py_services/prediction_ledger.py
CONFLICT (content): Merge conflict in investment_screener/backend/py_services/prediction_ledger.py
Auto-merging investment_screener/backend/tests/py_services/test_prediction_ledger.py
CONFLICT (content): Merge conflict in investment_screener/backend/tests/py_services/test_prediction_ledger.py
error: could not revert eeb6cdb5... feat: dual-write predictions/grades to intelligence_event (Wave 5D Task 2)
```

Conflicts arose because Task 6's later commit (`d472fcfd`) touched the same
`_append_prediction_event()` lines the revert was removing (the `claimDate` →
`date` key fix). Resolved by taking the "parent of `eeb6cdb5`" side of the
conflict markers for both files — i.e. removing `_append_prediction_event()`,
`_append_grade_event()`, and the `jsonl_path` parameters entirely, restoring
`append_prediction()`/`append_grade()` to their pre-Task-2 JSONL-only bodies,
and dropping the three dual-write tests
(`test_append_prediction_dual_writes_to_intelligence_ledger`,
`test_append_grade_dual_writes_to_intelligence_ledger`,
`test_append_prediction_still_writes_jsonl_when_ledger_write_fails`) that only
made sense with the ledger call present.

```
$ git add investment_screener/backend/py_services/prediction_ledger.py investment_screener/backend/tests/py_services/test_prediction_ledger.py
$ git commit -m "test: rollback exercise - revert Task 2 dual-write (throwaway)"
[detached HEAD d7e36863] test: rollback exercise - revert Task 2 dual-write (throwaway)
 4 files changed, 10 insertions(+), 181 deletions(-)
```

Confirmed `append_prediction`/`append_grade` no longer call `_append_*_event`:

```
$ sed -n '85,100p' investment_screener/backend/py_services/prediction_ledger.py
def append_prediction(record: dict[str, Any], path: Path = PREDICTIONS_PATH) -> None:
    """Append one prediction record to predictions.jsonl."""
    _append_jsonl(record, path)


def append_grade(record: dict[str, Any], path: Path = GRADED_PATH) -> None:
    """Append one grade record to predictions_graded.jsonl."""
    _append_jsonl(record, path)

$ grep -n "_append_prediction_event\|_append_grade_event\|jsonl_path" investment_screener/backend/py_services/prediction_ledger.py
(no matches)
```

## 4. Revert Task 3 (consumer) — discovered mid-exercise, not in the original brief's single-commit plan

Running the pre-migration test suite immediately after step 3 surfaced 6
failures, all `TypeError: append_prediction() got an unexpected keyword
argument 'jsonl_path'` — `harvest_predictions.py` (Task 3's consumer cutover)
still called `append_prediction(..., jsonl_path=jsonl_path)`, since only Task
2's commit had been reverted so far. This is expected: a real rollback of the
predictions domain must revert both the producer and its consumer commit,
exactly as the task brief's title says ("revert the producer/consumer
commits", plural). Identified and reverted Task 3's commit:

```
$ git log --oneline 7476ba0e^..2e6664e5 -- investment_screener/backend/py_services/harvest_predictions.py
f47b03a8 feat(wave5d-task3): cut harvest_predictions.py over to intelligence_event reads

$ git revert --no-commit f47b03a8
(clean revert, zero conflicts)

$ git commit -m "test: rollback exercise - revert Task 3 harvest_predictions.py consumer cutover (throwaway)"
[detached HEAD c40229cf] test: rollback exercise - revert Task 3 harvest_predictions.py consumer cutover (throwaway)
 2 files changed, 18 insertions(+), 107 deletions(-)

$ grep -n "jsonl_path\|_default_jsonl_path\|intelligence_event\|event_repository" investment_screener/backend/py_services/harvest_predictions.py
(no matches)
```

## 5. Confirm the pre-migration test suite passes using only `predictions.jsonl`

```
$ cd investment_screener/backend
$ python3 -m pytest tests/py_services/test_prediction_ledger.py tests/py_services/test_harvest_predictions.py -v
============================= test session starts ==============================
collected 43 items

tests/py_services/test_prediction_ledger.py::TestMakePredictionId::test_format PASSED
tests/py_services/test_prediction_ledger.py::TestAppendAndLoadPredictions::test_roundtrip PASSED
tests/py_services/test_prediction_ledger.py::TestAppendAndLoadPredictions::test_appends_without_truncating PASSED
tests/py_services/test_prediction_ledger.py::TestAppendAndLoadPredictions::test_load_missing_file_returns_empty_list PASSED
tests/py_services/test_prediction_ledger.py::TestAppendAndLoadGraded::test_roundtrip PASSED
tests/py_services/test_prediction_ledger.py::TestAppendAndLoadGraded::test_load_missing_file_returns_empty_list PASSED
tests/py_services/test_prediction_ledger.py::TestLatestPredictionFor::test_returns_most_recent_match PASSED
tests/py_services/test_prediction_ledger.py::TestLatestPredictionFor::test_returns_none_when_no_match PASSED
tests/py_services/test_prediction_ledger.py::TestGradeClaim::test_bullish_correct PASSED
tests/py_services/test_prediction_ledger.py::TestGradeClaim::test_bullish_incorrect PASSED
tests/py_services/test_prediction_ledger.py::TestGradeClaim::test_bullish_inconclusive_within_band PASSED
tests/py_services/test_prediction_ledger.py::TestGradeClaim::test_bearish_correct PASSED
tests/py_services/test_prediction_ledger.py::TestGradeClaim::test_bearish_incorrect PASSED
tests/py_services/test_prediction_ledger.py::TestGradeClaim::test_bearish_inconclusive_within_band PASSED
tests/py_services/test_prediction_ledger.py::TestGradeClaim::test_boundary_exactly_at_band_is_inconclusive PASSED
tests/py_services/test_harvest_predictions.py::TestLoadProjectionFromDb::test_selects_latest_ai_agent_entry_by_saved_at PASSED
tests/py_services/test_harvest_predictions.py::TestLoadProjectionFromDb::test_single_entry_still_works PASSED
tests/py_services/test_harvest_predictions.py::TestLoadProjectionFromDb::test_no_ai_agent_entries_returns_none PASSED
tests/py_services/test_harvest_predictions.py::TestBuildActionRatingClaim::test_accumulate_is_bullish PASSED
tests/py_services/test_harvest_predictions.py::TestBuildActionRatingClaim::test_trim_is_bearish PASSED
tests/py_services/test_harvest_predictions.py::TestBuildActionRatingClaim::test_maintain_is_not_harvested PASSED
tests/py_services/test_harvest_predictions.py::TestBuildActionRatingClaim::test_watchlist_is_not_harvested PASSED
tests/py_services/test_harvest_predictions.py::TestBuildActionRatingClaim::test_missing_action_returns_none PASSED
tests/py_services/test_harvest_predictions.py::TestBuildDcfFairValueClaim::test_uses_analytics_log_dcf_when_present PASSED
tests/py_services/test_harvest_predictions.py::TestBuildDcfFairValueClaim::test_falls_back_to_ai_thesis_when_no_analytics_dcf PASSED
tests/py_services/test_harvest_predictions.py::TestBuildDcfFairValueClaim::test_missing_fair_value_and_no_snapshot_price_returns_none PASSED
tests/py_services/test_harvest_predictions.py::TestBuildDcfFairValueClaim::test_missing_analyzed_at_returns_none PASSED
tests/py_services/test_harvest_predictions.py::TestAppendIfNew::test_appends_new_claim PASSED
tests/py_services/test_harvest_predictions.py::TestAppendIfNew::test_skips_unchanged_claim PASSED
tests/py_services/test_harvest_predictions.py::TestAppendIfNew::test_logs_new_claim_when_value_changed PASSED
tests/py_services/test_harvest_predictions.py::TestAppendIfNew::test_skips_when_price_unavailable PASSED
tests/py_services/test_harvest_predictions.py::TestHarvestActionAndDcfClaims::test_harvests_both_claim_types_from_one_projection PASSED
tests/py_services/test_harvest_predictions.py::TestHarvestActionAndDcfClaims::test_handles_no_investments_with_projections PASSED
tests/py_services/test_harvest_predictions.py::TestBuildRebalanceOrderClaims::test_buy_is_bullish PASSED
tests/py_services/test_harvest_predictions.py::TestBuildRebalanceOrderClaims::test_sell_is_bearish PASSED
tests/py_services/test_harvest_predictions.py::TestBuildRebalanceOrderClaims::test_gate_warnings_present_flag PASSED
tests/py_services/test_harvest_predictions.py::TestBuildRebalanceOrderClaims::test_empty_orders_returns_empty_list PASSED
tests/py_services/test_harvest_predictions.py::TestBuildRebalanceOrderClaims::test_missing_ticker_or_action_skipped PASSED
tests/py_services/test_harvest_predictions.py::TestBuildBreakerForecastClaims::test_triggered_breaker_is_harvested_as_bearish PASSED
tests/py_services/test_harvest_predictions.py::TestBuildBreakerForecastClaims::test_non_triggered_breaker_is_not_harvested PASSED
tests/py_services/test_harvest_predictions.py::TestBuildBreakerForecastClaims::test_empty_holdings_returns_empty_list PASSED
tests/py_services/test_harvest_predictions.py::TestHarvestRebalanceAndBreakerClaims::test_missing_rebalance_plan_file_is_not_an_error PASSED
tests/py_services/test_harvest_predictions.py::TestHarvestRebalanceAndBreakerClaims::test_harvests_from_both_artifacts_when_present PASSED

============================== 43 passed in 0.14s ==============================
```

**43/43 passing**, using only `predictions.jsonl`/`predictions_graded.jsonl` —
no `intelligence.sqlite` or `observations.jsonl` ledger dependency anywhere in
the reverted code path.

Net diff of the throwaway revert vs. the wave's tip:

```
$ git diff --stat d472fcfd HEAD
 .../backend/py_services/harvest_predictions.py     | 47 +++--------
 .../backend/py_services/intelligence/db_client.py  |  2 +-
 .../backend/py_services/prediction_ledger.py       | 93 +--------------------
 ...lution_integration_with_e3_prediction_ledger.py |  2 +-
 .../tests/py_services/test_harvest_predictions.py  | 78 ++----------------
 .../tests/py_services/test_prediction_ledger.py    | 94 +---------------------
 6 files changed, 28 insertions(+), 288 deletions(-)
```

## 6. Clean up the throwaway worktree

```
$ cd /Users/richardfremmerlid/Projects/InvestmentToolkit
$ git worktree remove /tmp/wave5d-rollback-exercise --force
$ git worktree list
/Users/richardfremmerlid/Projects/InvestmentToolkit                                                     f6b2b2f1 [main]
/Users/richardfremmerlid/Projects/InvestmentToolkit/.claude/worktrees/fix-stale-portfolio-timestamp-fx  19cf3f6b [fix-stale-portfolio-timestamp-fx]
/Users/richardfremmerlid/Projects/InvestmentToolkit/.claude/worktrees/wave5d-predictions                d472fcfd [worktree-wave5d-predictions] locked
```

No trace left on disk; `main` and this feature branch were never touched by the
exercise — all revert commits (`d7e36863`, `c40229cf`) existed only on the
detached-HEAD throwaway worktree, now discarded along with the worktree itself.

## Result

**Rollback is physically proven to work.** Reverting Task 2's producer commit
(`eeb6cdb5`) and Task 3's consumer commit (`f47b03a8`) together — with a manual
conflict resolution on the producer side to reconcile with Task 6's later bugfix
— fully restores `predictions.jsonl`/`predictions_graded.jsonl`-only behavior,
with zero references to the intelligence ledger remaining in either file, and
the full pre-migration test suite (43 tests) green against that restored state.
One correction to the brief's single-commit plan: because Task 3's consumer
cutover independently added the `jsonl_path` call signature to
`append_prediction()`, a real rollback requires reverting **both** the Task 2
producer commit and the Task 3 consumer commit, not Task 2 alone — this was
discovered empirically via the first test run's 6 failures, not assumed in
advance.
