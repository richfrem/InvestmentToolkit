-- Domain Data Model Schema (Account / Investment / Account_Investment)
-- Bounded context: portfolio construction, target/watchlist/holding lifecycle, valuation
-- pricing, and price-level/alert tracking. ADR-029, docs/architecture/domain-data-model.md
-- (Version 3.2 as of this file).
--
-- Status: DESIGNED, NOT YET APPLIED. Nothing in this file has been run against any real
-- database. Source of truth for the design itself is
-- docs/architecture/domain-data-model.md — if this file and that document ever diverge,
-- the document (and its git history of how the model got here) is authoritative.
--
-- Supersedes the schema previously named 03_big_domain_schema.sql (holdings +
-- target_portfolio_entry + target_portfolio_pillar/meta as separate root tables) — that
-- split was replaced after real-data review found it added a join to the two most common
-- query shapes in this app without a requirement forcing it. See the document's
-- "Revision History" (v1 -> v2 -> v3 -> v3.1 -> v3.2) for the full reasoning trail, not
-- duplicated here.
--
-- Depends on: instrument_id references below are INTENTIONALLY renamed to investment_id —
-- 01_intelligence_ledger_schema.sql's `instrument` table is absorbed into `investment`
-- here, not kept as a separate table. Applying this schema for real requires re-pointing
-- intelligence_event's existing instrument_id references (and event_repository.py /
-- replay_ledger.py / models.py / instrument_repository.py) at `investment` — a real,
-- small (2 dependent files, already measured) migration, not a zero-cost rename.

CREATE TABLE account (
    account_id      TEXT PRIMARY KEY,
    account_name    TEXT NOT NULL,
    account_type    TEXT,
    base_currency   TEXT NOT NULL DEFAULT 'CAD'
);

CREATE TABLE strategy_pillar (
    pillar_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    target_weight   REAL
);

CREATE TABLE sub_strategy (
    sub_strategy_id TEXT PRIMARY KEY,
    pillar_id       TEXT REFERENCES strategy_pillar(pillar_id),
    name            TEXT NOT NULL
);

-- Absorbs the old `instrument` (ticker identity) and `position`/`holdings`/
-- `target_portfolio_entry`/`watchlist_entry` (portfolio-universe stance) concepts into one
-- row per tracked thing — a security or a cash concept (CASH_USD/CASH_CAD).
CREATE TABLE investment (
    investment_id            TEXT PRIMARY KEY,   -- generated: ticker, or CASH_USD / CASH_CAD for cash concepts
    symbol                    TEXT NOT NULL,
    name                       TEXT,
    asset_class                 TEXT NOT NULL,     -- EQUITY, ETF, CASH, etc.
    currency                     TEXT NOT NULL DEFAULT 'USD',
    lifecycle_status               TEXT,            -- INITIATE|ACCUMULATE|MAINTAIN|TRIM|EXIT|WATCHLIST|AVOID|RESEARCH_ONLY
    target_weight                   REAL,
    target_action                    TEXT,
    -- target_entry_price intentionally NOT a column here — lives in price_level_tier
    -- (tier_kind='TARGET_ENTRY'): confirmed a genuine price level, not a scalar
    -- attribute (real data: never present without priceLevels, holds a materially
    -- different value than the buy tiers, e.g. SNDK target 1350 vs. buy tiers 1048/107).
    standing_decision_type            TEXT,
    standing_decision_reason           TEXT,
    standing_decision_source            TEXT,
    standing_decision_review             TEXT,
    pillar_id                             TEXT REFERENCES strategy_pillar(pillar_id),
    sub_strategy_id                        TEXT REFERENCES sub_strategy(sub_strategy_id),
    thesis_for_inclusion                    TEXT,
    agent_rationale                          TEXT,   -- most-recent-note convenience field; full history in investment_note
    is_watchlisted                            INTEGER NOT NULL DEFAULT 0,
    watchlist_added_at                         TEXT,
    latest_projection_id                        TEXT REFERENCES projection_version(projection_id),
    latest_research_event_id                     TEXT REFERENCES intelligence_event(event_id),
    thesis_breaker_status                         TEXT,
    updated_at                                     TEXT NOT NULL,
    UNIQUE(symbol)
);

CREATE INDEX idx_investment_pillar ON investment(pillar_id);
CREATE INDEX idx_investment_lifecycle ON investment(lifecycle_status);

-- Live-price cache, kept fresh by whichever existing flow already fetches quotes
-- (fetch_quotes.py, ta_sweep_batch.py's TV pull, BrokerSyncService.ts) via upsert.
CREATE TABLE investment_price (
    investment_id   TEXT PRIMARY KEY REFERENCES investment(investment_id),
    price            REAL NOT NULL,
    currency          TEXT NOT NULL DEFAULT 'USD',
    fetched_at         TEXT NOT NULL
);

-- Per-account actual holdings. TradingView CDP sync already receives per-account data
-- (accountType/accountId) — fetch_broker_data.py's write_snapshot() currently aggregates
-- it away before writing portfolio.json; this table is fed by NOT discarding that split.
-- Cash is modeled as a row with asset_class='CASH' pointing at a CASH_USD/CASH_CAD
-- investment row, not a NULL instrument_id.
CREATE TABLE account_investment (
    account_investment_id   TEXT PRIMARY KEY,   -- generated: account_id || ':' || investment_id
    account_id                TEXT NOT NULL REFERENCES account(account_id),
    investment_id               TEXT NOT NULL REFERENCES investment(investment_id),
    quantity                      REAL NOT NULL DEFAULT 0,
    average_cost                    REAL,
    book_value                        REAL,
    currency                           TEXT NOT NULL DEFAULT 'USD',
    last_synced_at                      TEXT NOT NULL,
    UNIQUE(account_id, investment_id)
);

CREATE INDEX idx_account_investment_account ON account_investment(account_id);
CREATE INDEX idx_account_investment_investment ON account_investment(investment_id);

CREATE TABLE price_level_set (
    price_level_set_id  TEXT PRIMARY KEY,
    investment_id          TEXT NOT NULL REFERENCES investment(investment_id),
    schema_version           TEXT,
    last_updated              TEXT,
    last_updated_by            TEXT,
    note                         TEXT
);

CREATE TABLE price_level_tier (
    tier_id               TEXT PRIMARY KEY,
    price_level_set_id      TEXT NOT NULL REFERENCES price_level_set(price_level_set_id),
    tier_kind                 TEXT NOT NULL DEFAULT 'BUY_TIER',  -- BUY_TIER (from priceLevels.buyTiers) | TARGET_ENTRY (from the old scalar targetEntryPrice)
    tier_number               INTEGER NOT NULL,
    price                      REAL,
    action                      TEXT,
    trim_pct                     REAL,
    order_type                    TEXT,
    basis                          TEXT,
    source                          TEXT,
    source_date                      TEXT,
    condition                         TEXT,
    status                             TEXT
);

-- TradingView alert mirror. A separate table from price_level_tier despite the same
-- conceptual shape (a price level tied to an investment) because write-ownership differs:
-- TradingView-synced/authoritative here, locally-authored in price_level_tier.
CREATE TABLE alert (
    alert_id        TEXT PRIMARY KEY,        -- TradingView's own alert_id — real external identity, not generated
    investment_id     TEXT REFERENCES investment(investment_id),  -- resolved from TV's "EXCHANGE:SYMBOL" (e.g. "NASDAQ:IREN" -> IREN)
    alert_type          TEXT,                 -- 'price', etc. — from TV's own type field
    message               TEXT,
    price                  REAL,
    condition_json           TEXT,             -- variable-shape condition structure (type/series) — kept as JSON, no evidence of field-by-field query need
    active                    INTEGER NOT NULL DEFAULT 1,
    resolution                 TEXT,
    created_at                   TEXT,
    last_fired_at                  TEXT,
    expiration_at                    TEXT,
    synced_at                          TEXT NOT NULL  -- when this row was last refreshed from TV, same role as account_investment.last_synced_at
);

CREATE INDEX idx_alert_investment ON alert(investment_id);

-- Dated history of thesis/rationale changes. Added because agentRationale in the source
-- JSON was found to be a single field with dated entries manually concatenated into one
-- ever-growing string (e.g. IREN: 5 dated entries in one string) — a real un-queryable-
-- history problem, not a hypothetical one. investment.agent_rationale becomes a
-- most-recent-note convenience field once this table exists; the full history lives here.
CREATE TABLE investment_note (
    note_id         TEXT PRIMARY KEY,
    investment_id     TEXT NOT NULL REFERENCES investment(investment_id),
    note_date           TEXT NOT NULL,
    note_type             TEXT,        -- e.g. 'THESIS_UPDATE', 'STANDING_DECISION_CHANGE'
    body                    TEXT NOT NULL,
    source                    TEXT      -- e.g. 'agent', 'grok_sweep', 'user'
);

CREATE INDEX idx_investment_note_investment ON investment_note(investment_id, note_date);

CREATE TABLE projection_version (
    projection_id         TEXT PRIMARY KEY,
    investment_id            TEXT NOT NULL REFERENCES investment(investment_id),
    version                    INTEGER NOT NULL,
    saved_at                    TEXT NOT NULL,
    analyzed_at                  TEXT,
    model                          TEXT,
    fair_value                      REAL,
    action                           TEXT,
    rationale                         TEXT,
    research_event_id                  TEXT REFERENCES intelligence_event(event_id),  -- real FK, not a filename string — the root cause of this whole effort's original bug
    snapshot_json                       TEXT,
    analytics_log_json                    TEXT,
    UNIQUE(investment_id, version)
);

CREATE INDEX idx_projection_investment ON projection_version(investment_id);

CREATE TABLE projection_scenario (
    scenario_id       TEXT PRIMARY KEY,
    projection_id       TEXT NOT NULL REFERENCES projection_version(projection_id),
    scenario_name         TEXT NOT NULL,       -- bear/base/bull — fixed set of 3, confirmed by real data
    weight                 REAL,
    growth_rate              REAL,
    net_margin                REAL,
    exit_pe                    REAL,
    quality_multiplier          REAL,
    share_change                  REAL,
    rationale                      TEXT,
    moat_score                      INTEGER,
    management_score                 INTEGER,
    year5_revenue                     REAL,
    year5_net_income                    REAL,
    year5_eps                            REAL,
    scenario_price                        REAL,
    risks_json                             TEXT,  -- small string array, no evidence of independent querying need
    UNIQUE(projection_id, scenario_name)
);

CREATE INDEX idx_projection_scenario_projection ON projection_scenario(projection_id);

-- Calculated views — market value, current %, target value, target quantity, rebalance
-- amount, cash weight are all computed here, never stored as authoritative columns.
CREATE VIEW account_total_value AS
SELECT
    ai.account_id,
    SUM(CASE WHEN i.asset_class = 'CASH' THEN ai.quantity ELSE ai.quantity * ip.price END) AS total_value,
    SUM(CASE WHEN i.asset_class = 'CASH' THEN ai.quantity ELSE 0 END) AS cash_value
FROM account_investment ai
JOIN investment i ON i.investment_id = ai.investment_id
LEFT JOIN investment_price ip ON ip.investment_id = ai.investment_id
GROUP BY ai.account_id;

CREATE VIEW portfolio_total_value AS
SELECT SUM(total_value) AS total_value FROM account_total_value;

CREATE VIEW investment_valuation AS
SELECT
    inv.investment_id,
    inv.symbol,
    COALESCE(SUM(ai.quantity), 0) AS current_quantity,
    ip.price,
    COALESCE(SUM(ai.quantity), 0) * ip.price AS market_value,
    COALESCE(SUM(ai.book_value), 0) AS book_value,
    (COALESCE(SUM(ai.quantity), 0) * ip.price) - COALESCE(SUM(ai.book_value), 0) AS unrealized_gain_loss,
    inv.target_weight,
    CASE WHEN pv.total_value > 0
         THEN (COALESCE(SUM(ai.quantity), 0) * ip.price) / pv.total_value
         ELSE NULL END AS current_weight,
    inv.target_weight * pv.total_value AS target_value,
    CASE WHEN ip.price > 0
         THEN (inv.target_weight * pv.total_value) / ip.price
         ELSE NULL END AS target_quantity,
    (inv.target_weight * pv.total_value) - (COALESCE(SUM(ai.quantity), 0) * ip.price) AS rebalance_amount
FROM investment inv
LEFT JOIN account_investment ai ON ai.investment_id = inv.investment_id
LEFT JOIN investment_price ip ON ip.investment_id = inv.investment_id
CROSS JOIN portfolio_total_value pv
GROUP BY inv.investment_id;

CREATE VIEW cash_weight AS
SELECT
    (SELECT SUM(quantity) FROM account_investment ai JOIN investment i ON i.investment_id = ai.investment_id WHERE i.asset_class = 'CASH')
    / (SELECT total_value FROM portfolio_total_value) AS cash_weight_pct;

-- Unchanged from 02_portfolio_operations_schema.sql: trade_log_entry, order_execution,
-- cash_flow, cash_flow_baseline. Their instrument_id columns now reference
-- investment(investment_id) instead of the old instrument(instrument_id) — not
-- redefined here to avoid duplicating that file's table definitions.
