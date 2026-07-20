# Wave 3 Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 3. This is a standalone, self-contained brief — do not assume the new
session has read any other document unless it's listed under "Required Reading" below.

---

## Current State (as of this handoff)

- **`main` is NOT yet updated with Wave 2.** Wave 2's work exists on branch
  `worktree-domain-model-v3-wave2`, commit `5ba96c0b`, as **PR #86**
  (`https://github.com/richfrem/InvestmentToolkit/pull/86`), open and awaiting review/merge.
- Before starting any Wave 3 work: confirm PR #86 is merged into `main`
  (`git log origin/main | grep 5ba96c0b` or check the PR's merge status directly — do not assume).
  If it is not yet merged, Wave 3 is **blocked** — stop and tell the user, do not proceed.
- `main`'s last confirmed commit before Wave 2 was `1df90086` (Wave 0 + Wave 1, merged via PR
  #84/#85).

## Current SQLite State (once Wave 2 is merged and a fresh checkout/rebuild is done)

`investment_screener/backend/data/domain_model.sqlite` is gitignored — not present on a fresh
checkout. Rebuild via:
```bash
cd investment_screener/backend/py_services
python3 -m domain_model.migrate_projections_to_sqlite --write   # Wave 1
python3 -m domain_model.migrate_target_portfolio_to_sqlite --write \
  --target-portfolio ../data/theses/target-portfolio.json \
  --watchlist ../data/watchlist.json \
  --alerts ../ARCHIVE/investment_screener/backend/data/tradingview_alerts_actual.json \
  --breaker-state ../data/thesis_breaker_state.json  # Wave 2 (note: alerts source is archived)
```
Real row counts as of Wave 2's completion (before any Wave 3 write):
- `investment`: 95
- `strategy_pillar`: 14
- `sub_strategy`: 14
- `price_level_set`: 8
- `price_level_tier`: 50
- `investment_note`: 73
- `alert`: 203
- `projection_version`: 115
- `projection_scenario`: 345

## Archived Domains (both Waves 1 and 2)

- **Wave 1**: `investment_screener/backend/data/projections/` → 82 files archived to
  `ARCHIVE/investment_screener/backend/data/projections/`.
- **Wave 2**: `watchlist.json` and `tradingview_alerts_actual.json` → archived to
  `ARCHIVE/investment_screener/backend/data/`.
- **Wave 2 retained exceptions (NOT archived, by explicit user decision — completed Retained-JSON
  Rationale Bar in the Wave 2 exit report)**: `target-portfolio.json` (real path:
  `data/theses/target-portfolio.json` — `ThesisService.ts`'s full-document CRUD needs fields with
  no SQLite column: `globalSettings`, `changeLog`, `schemaVersion`, per-pillar `bandConfig`,
  per-holding `shares`, full `thesisBreakers`/`standingDecision` sub-objects) and
  `thesis_breaker_state.json` (real per-breaker-id granularity a single scalar column can't
  represent). Do not assume these are gone or fully migrated — narrower read paths (pillars,
  holdings summary, watchlist flag, standingDecision scalars) ARE cut over to SQLite; the full
  document/multi-breaker structures are NOT.

## Remaining Domains (from the overall implementation plan)

- **Wave 3 (this wave)** — Account holdings (`portfolio.json`, gitignored — largest domain by the
  original plan's estimate: 20 producers, ~32 consumers). **Re-verify this count fresh before
  trusting it** — every wave so far (0, 1, 2) has found the plan's original inventory
  significantly wrong once real code was read. Wave 2 alone found 7 of 11 claimed producers were
  false positives, 2 real consumers were missing from the inventory entirely, and one producer was
  misattributed to the wrong file.
- **Wave 4** — Portfolio operations (trade log, order executions, cash flows). Not started.
- **Wave 5A–5E** — Generated research views (closes prior-effort debt) → TA sweep → daily briefs →
  predictions → account policy. Not started.

## Known Issues (carried into Wave 3, or newly relevant to it)

1. **`portfolio.json` is gitignored, private broker/account data.** Per spec §2.19 and CLAUDE.md's
   critical rules: NEVER overwrite/delete/modify without explicit user approval. The archive step
   for this domain (when Wave 3 reaches it) is **local-only** (`mv`, never `git mv`, never
   committed) — the privacy boundary that exists today must be identical after migration.
2. **Wave 2's two retained-JSON exceptions may share consumers with Wave 3's `portfolio.json`
   domain** — e.g. `BrokerSyncService.ts` was confirmed in Wave 2 to NOT touch
   `target-portfolio.json` (a stale docstring claim), but it very likely IS a real
   `portfolio.json` producer — re-verify fresh, do not assume Wave 2's findings about
   `BrokerSyncService.ts` extend to a different file.
3. **A background sub-agent dispatch hit an API session limit mid-file during Wave 2**, leaving
   a broken file in an orphaned worktree that had to be manually rescued. If dispatching large
   batches of file rewires to background agents in Wave 3 (this domain has the largest
   producer/consumer count of any wave so far), instruct them explicitly to commit after every
   single file (not batches), and independently verify — via direct test runs and grep, not by
   trusting the dispatch's self-report — before folding any orphaned worktree's work back in.
4. **Reference-data anomalies found in Wave 2** (14 auto-inferred `sub_strategy` placeholder
   names, 1 auto-inferred `strategy_pillar` placeholder name for `pillarId="other"`) are a
   product/governance question, not resolved. Not Wave 3's problem to fix, but worth knowing the
   `investment` table has these placeholder rows if Wave 3's account-holdings work ever joins
   against pillar/sub-strategy data.
5. **`investment.role` column and thesis-breaker-definition schema** were explicitly named as
   future migration triggers in Wave 2's exit report (for `update_thesis.py`/`thesis_breakers.py`'s
   still-JSON writes) — not Wave 3's scope, but a real, tracked, unresolved item for whoever
   eventually picks up that follow-up wave.

## Required Reading, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec (§2.4 specifically covers the account-holdings/`portfolio.json` domain: 20
   producers, ~32 consumers per the original estimate, `LOCAL_PRIVATE_ARCHIVE` classification,
   target tables `account_investment`/`investment_price`).
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the overall
   wave roadmap, Global Constraints, Definition of Done, Wave KPI table template — binding on
   every wave.
3. `docs/superpowers/status/wave1-projections-report.md` and `wave1-handoff.md` — Wave 1's
   reference example of "done" (smallest domain, 2 producers/18 consumers).
4. `docs/superpowers/status/wave2-target-portfolio-report.md` and `wave2-handoff.md` — Wave 2's
   exit report (this wave, larger domain, 6 producers/23 consumers after inventory correction) —
   **read this one especially closely**: it documents the exact kind of plan-inventory
   corrections, real bugs, and architecture-boundary findings Wave 3 should expect to encounter
   given it's an even larger domain.
5. This file's "Way of Working" section is intentionally NOT reproduced here — it lives in
   `docs/superpowers/status/wave2-kickoff-prompt.md`'s "Way of Working" section (still the
   authoritative reusable template: Setup → Plan the wave → Execute with wave-level conditional
   autonomy → Wave exit). Copy that section forward unchanged; only this file's "This Wave's
   Scope"/"Starting State"/"Do Not" sections are Wave-3-specific.

**Amendment to the Way of Working, formalized during Wave 2, binding on Wave 3 and beyond:**
Wave-level conditional autonomy — do not dispatch an independent review after every task; execute
the approved wave plan end-to-end, fixing issues found along the way. Perform exactly two
comprehensive review points: (1) the dry-run gate, before any real data write, and (2) the exit
report, before the PR is opened. Hard-stop conditions still apply in full (parity mismatch,
unexplained row-count delta, new data shape without a test, a producer/consumer still on the old
JSON path, a repository-layer bypass, new test failures, archive-readiness grep still finding real
I/O, an archive step that would remove rollback capability, a permanent unexamined hybrid state).

## This Wave's Scope (Wave 3)

Per the overall plan's §2.4: **Account holdings** — `portfolio.json` (gitignored, real broker/
account data: TFSA + RRSP positions, cash balances). Original estimate (re-verify before trusting):

**Claimed producers (20):** `BrokerSyncService.ts`, `routes/portfolio.ts`, `ThesisService.ts`,
`market_regime.py`, `risk_engine.py`, `backtest_harness.py`, `apply_portfolio_updates.py`,
`rebalancer.py`, `extract_portfolio_symbols.py`, `thesis_breakers.py`, `ta_sweep_batch.py`,
`fetch_broker_data.py`, `place_order.py`, `fetch_financials.py`, `ytd_return.py`,
`relabel_actions.py`, `validate_weights.py`, `update_price_levels.py`, `update_thesis.py`,
`daily_brief.py`.

**Claimed consumers (~32):** `helpers.ts`, `docs.ts`, `stock.ts`, `screener.ts`, `theses.ts`,
`compute_conviction_scores.py`, `overnight_gaps.py`, `order_risk_gates.py`,
`earnings_calendar.py`, `lock_and_normalize_targets.py`, `earnings_expectations.py`,
`verify_portfolio_total.py`, `verify_thesis_sync.py`, `portfolio_performance.py`,
`harvest_predictions.py`, `Sidebar.tsx`, `PortfolioModal.tsx`, `Settings.tsx`,
`PortfolioTable.tsx`, `tv_create_alerts.py`, `dcf_sensitivity.py`, `standardize_metrics.py`,
`comps_valuation.py`, `generate_reports.py`, `watchlist_manager.py`, `generate_review.py`,
`scan_opportunities.py`, `weekly_review.py`, `portfolio_action.py`, `verify_refresh.py`,
`generate_portfolio_blueprint.py`, `dcf_scenarios.py`.

**Target schema (already created by Wave 0, per the spec):** `account_investment` (quantity,
average_cost, book_value, currency, last_synced_at), `investment_price` (price cache — per
CLAUDE.md pitfall #27, never an external FX API, always inferred from TradingView native values).

**Highest-risk item, per the spec:** this is the largest domain by producer/consumer count in the
entire migration — deliberately not attempted before Waves 1-2 proved the pattern. Budget real
investigation time accordingly; strongly consider sub-waves (like Wave 1's 7A/7B/7C) for the
consumer-rewiring portion, given Wave 2 already needed to split producer work from consumer work
across 2-3 dispatch batches to manage session-limit risk.

**Archive rule reminder (different from Waves 1-2):** `portfolio.json` is gitignored — the archive
step is **local-only** `mv` (never `git mv`, never `git add`ed), per spec §2.19. The privacy
boundary that exists today (never committed) must be identical after migration.

**Validation requirement, per the spec:** parity must be proven across at least one full real
broker-sync cycle before archiving — not a one-off snapshot diff, since this is live, syncing
data (TFSA/RRSP positions change with every trade and price refresh), unlike Waves 1-2's more
static target/watchlist/projection data.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec's producer/
  consumer counts above — treat them as a starting hypothesis to verify, not ground truth (every
  prior wave found them wrong).
- Do not run a real data migration without the dry-run-then-approval gate.
- Do not archive anything before every Hard-Stop Condition gate is independently confirmed true.
- Do not `git add`/`git mv` any part of `portfolio.json` or its archived copy — it is gitignored,
  private, real financial data. Archive with a local-only `mv`, never committed.
- Do not merge to `main` yourself without being told to.
- Do not start Wave 4 after this wave's exit — stop and wait for review, same as Waves 1 and 2.
