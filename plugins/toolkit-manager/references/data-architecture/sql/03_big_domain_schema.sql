-- Big-Domain Schema: holdings, target_portfolio_entry, projection_version
-- Replaces portfolio.json, target-portfolio.json, projections/*.json respectively —
-- the three domains carrying 69% of this repo's JSON file count and 54% of its
-- JSON-referencing code (docs/architecture/big-domain-migration-design.md).
--
-- Status: DESIGNED, NOT YET APPLIED. None of these tables exist anywhere in the
-- codebase today. This is new DDL authored from the column-level design in
-- docs/architecture/big-domain-migration-design.md, not an export of anything live.
--
-- Implementation order per ADR-029 §5: projection_version first (1 real producer at
-- design time vs. 11-20 for the other two). target_portfolio_entry and holdings do
-- not start until projection_version's producer/consumer/archive cycle is proven
-- end-to-end.

-- =============================================================================
-- Phase 1 (approved next step): projection_version — replaces projections/*.json
-- =============================================================================

CREATE TABLE IF NOT EXISTS projection_version (
    projection_id         TEXT PRIMARY KEY,             -- instrument_id || ':' || version
    instrument_id          TEXT NOT NULL REFERENCES instrument(instrument_id),
    version                 INTEGER NOT NULL,
    saved_at                TEXT NOT NULL,
    analyzed_at              TEXT,
    model                    TEXT,
    fair_value               REAL,
    action                   TEXT,                       -- INITIATE|ACCUMULATE|MAINTAIN|TRIM|EXIT|WATCHLIST (CLAUDE.md pitfall #6)
    rationale                 TEXT,
    research_event_id        TEXT REFERENCES intelligence_event(event_id),  -- real FK, not a filename string — ADR-029 §6
    snapshot_json             TEXT,                       -- price/currency/market-data snapshot at analysis time
    scenarios_json             TEXT,                      -- bear/base/bull scenario detail, deliberately kept nested
    analytics_log_json         TEXT,
    UNIQUE(instrument_id, version)
);

CREATE INDEX IF NOT EXISTS idx_projection_instrument ON projection_version(instrument_id);
CREATE INDEX IF NOT EXISTS idx_projection_action ON projection_version(action);
CREATE INDEX IF NOT EXISTS idx_projection_research_event ON projection_version(research_event_id);

-- =============================================================================
-- Phase 2: target_portfolio_entry — replaces target-portfolio.json
-- Fulfills ADR-028's pre-approved "portfolio_decision" table slot.
-- =============================================================================

CREATE TABLE IF NOT EXISTS target_portfolio_entry (
    instrument_id       TEXT PRIMARY KEY REFERENCES instrument(instrument_id),
    target_weight        REAL NOT NULL,
    standing_decision     TEXT,              -- BUY/SELL/HOLD anchor, CLAUDE.md rule #8 — safety-critical, needs its own test
    role                  TEXT,              -- e.g. 'core', 'exited'
    pillar                TEXT,
    sub_strategy          TEXT,
    target_entry_price    REAL,
    agent_rationale        TEXT,
    updated_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS target_portfolio_pillar (
    pillar_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    target_weight   REAL
);

CREATE TABLE IF NOT EXISTS target_portfolio_meta (
    id                      TEXT PRIMARY KEY,      -- fixed value: 'target-portfolio'
    schema_version           INTEGER NOT NULL,
    doc_version              INTEGER NOT NULL,      -- whole-document version counter, preserved from the JSON's semantics
    description               TEXT,
    created_at                TEXT NOT NULL,
    updated_at                TEXT NOT NULL,
    global_settings_json       TEXT                 -- small, rarely-queried config blob, kept as JSON deliberately
);

CREATE INDEX IF NOT EXISTS idx_target_portfolio_pillar ON target_portfolio_entry(pillar);

-- =============================================================================
-- Phase 3: holdings — replaces portfolio.json
-- portfolio.json is a broker mirror (RETAIN_AS_EXTERNAL_CACHE reasoning still
-- applies to the SOURCE OF TRUTH — TradingView remains authoritative even after
-- this table exists; this table is the local queryable cache, same role
-- portfolio.json plays today, just queryable).
-- =============================================================================

CREATE TABLE IF NOT EXISTS holdings (
    holding_id      TEXT PRIMARY KEY,      -- generated: instrument_id || ':' || account
    instrument_id   TEXT NOT NULL REFERENCES instrument(instrument_id),
    account         TEXT NOT NULL,          -- e.g. TFSA, RRSP
    shares          REAL NOT NULL,
    avg_price       REAL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    last_synced_at  TEXT NOT NULL,          -- ISO timestamp of last broker sync
    UNIQUE(instrument_id, account)
);

CREATE TABLE IF NOT EXISTS portfolio_totals (
    snapshot_id             TEXT PRIMARY KEY,  -- generated: last_synced_at
    total_equity_usd         REAL,
    total_equity_cad         REAL,
    cash_usd                  REAL,
    cash_cad                  REAL,
    fx_rate_usd_cad           REAL,            -- CLAUDE.md pitfall #27: inferred from TV native values, never external FX API
    last_synced_at            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_holdings_account ON holdings(account);
CREATE INDEX IF NOT EXISTS idx_holdings_instrument ON holdings(instrument_id);
