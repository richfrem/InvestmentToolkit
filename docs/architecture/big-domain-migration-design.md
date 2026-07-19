# Big-Domain Migration Design: holdings, target_portfolio_entry, projection_version

Full column-level design for the three domains identified as carrying the actual architectural
value of this migration: `portfolio.json`, `target-portfolio.json`, `projections/*.json`. No
code has been written. This document exists to be reviewed and corrected before any
implementation starts, and to answer directly: if these three migrate, how much does
persistence complexity actually go down.

Producer/consumer counts below are real — gathered by grepping every referencing file for
`json.load`/`readFile` (read) vs `json.dump`/`writeFile` (write) patterns, not estimated.

---

## 1. `holdings` (replaces `portfolio.json`)

### Column-level schema

```sql
CREATE TABLE holdings (
    holding_id      TEXT PRIMARY KEY,      -- generated: instrument_id || ':' || account
    instrument_id   TEXT NOT NULL REFERENCES instrument(instrument_id),
    account         TEXT NOT NULL,          -- e.g. TFSA, RRSP
    shares          REAL NOT NULL,
    avg_price       REAL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    last_synced_at  TEXT NOT NULL,          -- ISO timestamp of last broker sync
    UNIQUE(instrument_id, account)
);

CREATE TABLE portfolio_totals (
    snapshot_id            TEXT PRIMARY KEY,  -- generated: last_synced_at
    total_equity_usd        REAL,
    total_equity_cad        REAL,
    cash_usd                 REAL,
    cash_cad                 REAL,
    fx_rate_usd_cad          REAL,            -- per CLAUDE.md pitfall #27, inferred from TV native values, never external API
    last_synced_at           TEXT NOT NULL
);

CREATE INDEX idx_holdings_account ON holdings(account);
CREATE INDEX idx_holdings_instrument ON holdings(instrument_id);
```

`tvSnapshot` (the third top-level key in the current `portfolio.json`) is raw broker-sync
diagnostic data (per CLAUDE.md pitfall #27's exchange-rate note) — represented above as
`portfolio_totals` columns rather than a preserved blob, since its fields (`totalEquityCADCombined`
etc.) are exactly the columns the app needs to query, not opaque payload.

### Migration strategy

1. Write `portfolio_ledger/holdings_repository.py` (+ TS equivalent) with `upsert_holding()`,
   `list_holdings(account=None)`, `get_totals()`.
2. `BrokerSyncService.ts` and `fetch_broker_data.py` — the only two real sync-time producers —
   switch from writing `portfolio.json` to calling the repository's upsert.
3. Every consumer switches from `fs.readFile(PORTFOLIO_FILE)` to a repository read call.
4. Run both paths in parallel for one full sync cycle, diff JSON output against SQL query
   output row-for-row (same byte-parity discipline used for the research migration).
5. Only after parity is proven and every real consumer is confirmed migrated: `git mv
   portfolio.json ARCHIVE/investment_screener/backend/data/portfolio.json.pre-migration` (this
   file is gitignored/private — archiving it locally, not committing the actual holdings data;
   only the migration event itself needs to be documented).

### Producer inventory (writes=1+, real code changes required)

`BrokerSyncService.ts`, `investment_screener/backend/src/routes/portfolio.ts`,
`ThesisService.ts`, `market_regime.py`, `risk_engine.py`, `backtest_harness.py`,
`apply_portfolio_updates.py`, `rebalancer.py`, `extract_portfolio_symbols.py`,
`thesis_breakers.py`, `ta_sweep_batch.py`, `fetch_broker_data.py`, `place_order.py`,
`fetch_financials.py`, `ytd_return.py`, `relabel_actions.py`, `validate_weights.py`,
`update_price_levels.py`, `update_thesis.py`, `daily_brief.py` — **20 real producers.**
(`audit_json_usage.py` excluded — it only contains the string "portfolio.json" as a
classification pattern, it doesn't write portfolio data; confirmed by reading the match context.)

### Consumer inventory (read-only, need a read-path swap)

`helpers.ts`, `docs.ts`, `stock.ts`, `screener.ts`, `theses.ts`, `compute_conviction_scores.py`,
`overnight_gaps.py`, `order_risk_gates.py`, `earnings_calendar.py`,
`lock_and_normalize_targets.py`, `earnings_expectations.py`, `verify_portfolio_total.py`,
`verify_thesis_sync.py`, `portfolio_performance.py`, `harvest_predictions.py`,
`Sidebar.tsx`, `PortfolioModal.tsx`, `Settings.tsx`, `PortfolioTable.tsx`, `tv_create_alerts.py`,
`dcf_sensitivity.py`, `standardize_metrics.py`, `comps_valuation.py`, `generate_reports.py`,
`watchlist_manager.py`, `generate_review.py`, `scan_opportunities.py`, `weekly_review.py`,
`portfolio_action.py`, `verify_refresh.py`, `generate_portfolio_blueprint.py`, `dcf_scenarios.py`
— **~32 real read-only consumers.**

### Archive criteria

All 20 producers write via the repository, all ~32 consumers read via the repository, byte-parity
proven across at least one full sync cycle, zero remaining `fs.readFile`/`json.load` calls
against `portfolio.json`'s literal path (verifiable by grep returning zero I/O matches, doc/audit
mentions excluded).

### Rollback strategy

Restore `portfolio.json` from `ARCHIVE/`, revert the producer/consumer commits (all real code
changes, so a normal `git revert` applies), no data loss since the repository writes were
additive/parallel during the transition period, never destructive to the JSON file until archive
step.

---

## 2. `target_portfolio_entry` (replaces `target-portfolio.json`)

### Column-level schema

```sql
CREATE TABLE target_portfolio_entry (
    instrument_id       TEXT PRIMARY KEY REFERENCES instrument(instrument_id),
    target_weight        REAL NOT NULL,
    standing_decision     TEXT,              -- BUY/SELL/HOLD anchor, CLAUDE.md rule #8
    role                  TEXT,              -- e.g. 'core', 'exited'
    pillar                TEXT,
    sub_strategy          TEXT,
    target_entry_price    REAL,
    agent_rationale        TEXT,
    updated_at             TEXT NOT NULL
);

CREATE TABLE target_portfolio_pillar (
    pillar_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    target_weight   REAL
);

CREATE TABLE target_portfolio_meta (
    id              TEXT PRIMARY KEY,       -- fixed 'target-portfolio'
    schema_version  INTEGER NOT NULL,
    doc_version     INTEGER NOT NULL,       -- whole-document version counter, preserved
    description     TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    global_settings_json TEXT               -- small, rarely-queried config blob kept as JSON deliberately
);

CREATE INDEX idx_target_portfolio_pillar ON target_portfolio_entry(pillar);
```

`globalSettings` stays a JSON column deliberately — it's config, not queried row-by-row, same
reasoning as `account_policy.json` staying JSON elsewhere in this plan.

### Migration strategy

Same 5-step shape as `holdings` above: repository first, producers switch, consumers switch,
parity proof, then archive. **The `standingDecision` anchor rule (CLAUDE.md #8 — never flip
BUY→SELL on <15% variance) must be re-verified against the new read path specifically**, since
it's the single most safety-critical piece of logic touching this file.

### Producer inventory

`BrokerSyncService.ts`, `market_regime.py`, `risk_engine.py`, `rebalancer.py`,
`backtest_harness.py`, `thesis_breakers.py`, `ta_sweep_batch.py`, `daily_brief.py`,
`update_thesis.py`, `validate_weights.py`, `update_price_levels.py` — **11 real producers.**

### Consumer inventory

`docs.ts`, `stock.ts`, `screener.ts`, `theses.ts`, `compute_conviction_scores.py`,
`order_risk_gates.py`, `lock_and_normalize_targets.py`, `earnings_expectations.py`,
`verify_thesis_sync.py`, `harvest_predictions.py`, `tv_create_alerts.py`, `generate_review.py`,
`verify_refresh.py`, `generate_portfolio_blueprint.py`, `generate_reports.py`,
`scan_opportunities.py`, `weekly_review.py`, `portfolio_action.py` — **~18 real consumers.**

### Archive criteria / Rollback strategy

Same discipline as `holdings`. This file is git-tracked (not gitignored), so the archive step
here is a real `git mv target-portfolio.json ARCHIVE/...` with full history preserved, not a
local-only backup.

---

## 3. `projection_version` (replaces `projections/*.json`, 144 files)

### Column-level schema

```sql
CREATE TABLE projection_version (
    projection_id         TEXT PRIMARY KEY,   -- instrument_id || ':' || version
    instrument_id          TEXT NOT NULL REFERENCES instrument(instrument_id),
    version                 INTEGER NOT NULL,
    saved_at                TEXT NOT NULL,
    analyzed_at              TEXT,
    model                    TEXT,
    fair_value               REAL,
    action                   TEXT,             -- INITIATE|ACCUMULATE|MAINTAIN|TRIM|EXIT|WATCHLIST (CLAUDE.md pitfall #6)
    rationale                 TEXT,
    research_report_pointer   TEXT,             -- the field this whole session's bug lived in
    snapshot_json             TEXT,             -- price/currency/market-data snapshot at analysis time
    scenarios_json             TEXT,            -- bear/base/bull scenario detail — nested, not flattened to columns
    analytics_log_json         TEXT,
    UNIQUE(instrument_id, version)
);

CREATE INDEX idx_projection_instrument ON projection_version(instrument_id);
CREATE INDEX idx_projection_action ON projection_version(action);
```

`scenarios_json`/`snapshot_json`/`analytics_log_json` stay JSON columns deliberately — this is
where the "not everything is a flat row" lesson from the smaller domains applies in reverse: DCF
scenario math has deeply nested, variable-shape detail that isn't queried field-by-field the way
`fair_value`/`action`/`research_report_pointer` are. Flattening those into 30+ columns would add
schema churn every time a valuation script's output shape changes, for no query benefit.

### Migration strategy

1. `ProjectionService.ts`'s `saveProjection()` — confirmed via code read to be the actual sole
   producer (validates data, manages version increments, atomic writes) — becomes the only
   thing that writes `projection_version` rows. This is the cleanest of the three domains
   because there's already exactly one producer, not 20.
2. Rewire the `researchReport` pointer mechanism at the same time — this is the field
   responsible for this entire session's original bug, and it needs to be redesigned as part of
   this move, not carried over unchanged.
3. Every consumer switches from reading `projections/{TICKER}.json` to a repository query.
4. Parity proof per ticker (144 files → 144 row-groups, diffed).
5. Archive: `git mv investment_screener/backend/data/projections/
   ARCHIVE/investment_screener/backend/data/projections/` (144 files, one commit, full history
   preserved).

### Producer inventory

`ProjectionService.ts` is the real, sole write path (confirmed by code inspection: it owns
version increments and atomic writes). `audit_json_usage.py`'s 2 write-matches are the
audit tool's own report generation, not projection data — excluded. **1 real producer.**

### Consumer inventory

`ThesisService.ts`, `compute_conviction_scores.py`, `rebalancer.py`, `framework_score.py`,
`ta_sweep_batch.py`, `persist_etf_analysis.py`, `watchlist_manager.py`, `comps_valuation.py`,
`generate_review.py`, `portfolio_action.py`, `consolidate_research.py`, `scan_opportunities.py`,
`verify_refresh.py`, `update_price_levels.py`, `generate_portfolio_blueprint.py` — **~15 real
consumers**, plus `ThesisService.ts` and `ProjectionService.ts` both read as well as write
(version history lookups). `TradePrepModal.tsx`, `api.ts`, `peer_bench.py`, `local_api.py`,
`generate_grok_prompt.py`, `apply_catalyst.py` matched the grep by mentioning "projections" as a
path/type reference with no actual I/O call — need direct confirmation before counting as real
consumers, flagged rather than assumed.

### Archive criteria / Rollback strategy

Same discipline. Rollback restores 144 files from `ARCHIVE/` via `git mv` back, reverts producer
commit (single service, low risk), reverts consumer commits.

---

## Complexity Reduction — Answering the Actual Question

**How many JSON files disappear:** `portfolio.json` (1) + `target-portfolio.json` (1) +
`projections/*.json` (144) = **146 files**, out of 212 total JSON/JSONL files catalogued
repo-wide. That's **69% of the file count** — but file count overstates it, since 144 of those
146 are one-per-ticker instances of the same schema, not 144 independently-shaped domains.

**How many consumers move:** 82 unique files reference at least one of these three domains
(deduplicated — many files reference more than one), out of 151 total files that reference any
JSON/JSONL in the entire repository. That's **54% of all JSON-referencing code** — the majority
of the codebase's JSON dependency lives in exactly these three domains.

**What this proves:** the reviewer's "80% of the value" framing holds up under real numbers —
these three domains are not just architecturally central, they are where most of the actual
JSON coupling in this codebase lives. Migrating them would be the first time this whole effort
touches something close to the scale the original objective implied.

**What this doesn't change:** nothing has moved yet. This is still design. The next step, per
your direction, is `projections/*.json` first — and per the table above, it has the smallest
real producer count (1) of the three, even though its consumer count (≈15-23) sits in the
middle. That's a meaningful data point in its favor as the starting point beyond "it sits in the
middle of the system": one producer means one place to get the write path right before rewiring
15+ read paths.
