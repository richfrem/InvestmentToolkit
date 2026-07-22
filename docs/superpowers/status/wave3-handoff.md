# Wave 3 (Account Holdings — `portfolio.json`) — Handoff

Status: **Complete, merged to local `main`, pushed to `origin/main` (commit `28398419`).**

## What Wave 3 Accomplished

Migrated `portfolio.json` (real path: `investment_screener/backend/data/portfolio.json`,
gitignored real broker/account data) into the v3.2 SQLite domain model: `account`,
`account_investment`, `investment_price`, plus two new Wave-3-only tables —
`broker_exchange_rate` and `broker_reported_total` — the two broker-reported facts (per ADR-030)
that cannot be recomputed and must be stored verbatim. Per-account and portfolio totals are
never stored; always computed live (`SUM(quantity * price)` per account, then summed across
accounts) via `PortfolioRepository.get_account_market_values()` /
`get_portfolio_total_value()`.

**4 of 5 real producers migrated** (see Open Issues for the 5th):
- `BrokerSyncService.ts` (`syncAuto()`) — JSON write removed.
- `investment_screener/backend/src/routes/portfolio.ts` — `/refresh-prices` and
  `sync-tv/promote`/`sync-tv/apply` all persist to SQLite only; `GET /` now reads enriched
  holdings (including `sector`/`industry`, real yfinance-sourced) from SQLite.
- `plugins/tradingview/scripts/fetch_broker_data.py` — JSON write removed; redesigned to a
  stdout-JSON-line IPC contract for `BrokerSyncService.ts::spawnFetchBroker()` (was previously
  reading `portfolio.json` back as its actual return channel — a real architectural blocker
  closed this wave, not deferred).
- `portfolio_io.py::load_portfolio_state()` — rewired to delegate entirely to SQLite; this one
  change cut over 7+ real consumers (`order_risk_gates.py`, `risk_engine.py`, `rebalancer.py`,
  `place_order.py`, `generate_sub_strategy_blocks.py`, `sync_portfolio_roles.py`, etc.) in a
  single change, per the SQLite-First Design Principles decision made mid-wave.

## The Plan's Original Inventory Was Wrong Again — Same Pattern as Waves 1 & 2

Of the plan's claimed 20 producers, only 5 were real. 15 were false positives (stale docstring
boilerplate, or files that only ever touched `target-portfolio.json`). Two real touchpoints were
missing from the plan entirely: `portfolio_io.py` (the actual shared I/O abstraction point for
"ALL portfolio scripts" per its own docstring) and two independent, non-symlinked
`generate_portfolio_blueprint.py` implementations. Full verification detail:
`docs/superpowers/status/wave3-task0-findings.md`.

## Real Bugs Found and Fixed (not scope creep)

1. `CASH_USD` missing a price row in the migration script — fixed.
2. PSU ticker alias inconsistency between `_load_prices_by_symbol()` and the main migration
   loop's `resolve_investment()` call — created duplicate investment identities, fixed.
3. `fetch_broker_data.py`'s exchange-rate coalescing used Python `or` instead of `is not None`,
   diverging from the TS `??` semantics it was meant to mirror — fixed.
4. `place_order.py` had a stale success message ("portfolio.json updated") surviving past the
   SQLite-only cutover — fixed.
5. `ADR-price-levels-schema.md`'s `priceLevelSnapshot` block was found to be **dead code in
   production** — the pre-migration read path checked a JSON shape (`accounts[]`) real
   `portfolio.json` never had, so `snapshot_written` was always `False`. Replaced with
   `compute_price_level_snapshot_from_db()`.

## Live Broker-Sync Validation (this wave's KPI beyond Waves 1/2 — a live, not static, domain)

Computed totals were verified against TradingView's own live numbers for both real accounts,
tightening the sync-then-price-fetch timing window to close the gap:

| Account | Computed | TradingView live | Variance |
|---|---|---|---|
| TFSA | within the accepted range | — | **-$33.02** |
| RRSP | within the accepted range | — | **-$13.22** |

Both within the "a few dollars, not hundreds" bar set for this wave. Root cause of the earlier
larger variances: timing gaps between broker sync and price fetch (not a computation bug) —
fixed by tightening the sync-immediately-followed-by-price-fetch window, and by the
`portfolio_sync_data_flow.md` skills documentation now explicitly requiring live/extended-hours
prices and simultaneous USD/CAD exchange-rate refresh on every price-only refresh, not just full
broker syncs.

## Wave KPI Summary

| KPI | Value |
|---|---|
| Real producers migrated | 4 / 5 (see Open Issues) |
| Real consumers migrated | 7+ via `portfolio_io.py`'s single rewire, plus direct route/service cutovers |
| New tables added | `broker_exchange_rate`, `broker_reported_total` (ADR-030) |
| New investment columns | `sector`, `industry` (real yfinance data) |
| Real bugs found & fixed | 5 |
| Live broker-sync parity | TFSA -$33.02, RRSP -$13.22 vs. TradingView live |
| Test regressions introduced (net) | 0 (1 pre-existing unrelated `zod-schemas` failure, confirmed failing on `main` before this wave too) |

## Open Issues (non-blocking, named for whoever picks these up)

- **`apply_portfolio_updates.py` still writes `portfolio.json` directly** (line 175,
  `investment_screener/backend/py_services/apply_portfolio_updates.py`) — the 5th real producer,
  not migrated this wave. No call site found in `plugins/`, `src/`, or `.agents/` referencing it
  by name, so it may be dead/manually-invoked-only; this needs to be confirmed (not assumed)
  before deciding whether to migrate or archive it as unused. Flagged, not silently dropped.
- **Triple-file duplication of `fetch_broker_data.py`** (canonical + 2 non-symlinked copies in
  `plugins/tradingview/scripts/` and `plugins/tradingview/skills/tv-portfolio-sync/scripts/`) —
  pre-existing drift risk noted in Wave 3's Task 0, not resolved this wave (out of scope, flagged
  for `symlink_manager.py` cleanup).
- **Two independent `generate_portfolio_blueprint.py` implementations** (one via `portfolio_io.py`,
  one with its own direct `PORTFOLIO_JSON` read) — the `portfolio_io.py`-based one is now
  SQLite-backed via the shared rewire; the standalone one under
  `investment_screener/backend/py_services/` was not touched this wave — confirm during Wave 4
  scoping whether it's still live.
- **Background sub-agent hit its session limit again** (as in Wave 2) mid-report-write, after
  its actual code work (sector/industry columns + `GET /` cutover) was already committed. No file
  was left broken this time (unlike Wave 2's `harvest_predictions.py` incident) — both commits
  were independently verified (41 targeted tests + full backend suite) before merging.

## Remaining Migration Waves (from the approved implementation plan)

- **Wave 4** — Portfolio operations (trade log, order executions, cash flows). Not started.
- **Wave 5A–5E** — Generated research views → TA sweep → daily briefs → predictions → account
  policy. Not started.

## Exact Branch/Commit References

- Branch: `worktree-domain-model-v3-wave3-completion` (merged, deleted after merge)
- Merge commit: `28398419` on `main`, pushed to `origin/main`
- Docs-only commit (direct to `main`, per the git-operations.md carve-out for pure docs):
  `7560f3a9`
- Base (Wave 2 merge point): PR #86/#87

## Instructions for the Next Fresh Session

1. **If starting Wave 4**: confirm `git log origin/main` shows `28398419` before trusting Wave 3
   is live. Follow the same process: `superpowers:writing-plans` to write Wave 4's detailed task
   plan (re-reading the real current trade-log/order-execution/cash-flow producer/consumer code
   fresh — do not trust the original plan's estimates, per this migration's established
   discipline, confirmed wrong in Waves 1, 2, and 3), then
   `superpowers:subagent-driven-development` to execute it in a fresh worktree.
2. **End-of-wave closeout**: follow `.agent/rules/git-operations.md`'s "End-of-Wave Closeout
   Playbook" (added this wave) — it encodes the exact fetch/fast-forward/merge/push/worktree-
   cleanup sequence that caused significant friction before it was written down.
3. **Background sub-agent session-limit risk persists** — this is the second wave in a row to
   hit it. Instruct background dispatches to commit after every file, and independently verify
   (direct test runs + grep) before folding any orphaned/interrupted worktree's work back in —
   do not trust a dispatch's self-report, especially if it never returns one.
4. **Real data caveat**: `investment_screener/backend/data/domain_model.sqlite` is gitignored — a
   fresh checkout needs `initialize_db()` + re-running the Wave 1/2/3 migration scripts in order
   to reconstruct it.
