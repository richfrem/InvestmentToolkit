-- 0001_baseline: the domain_model.sqlite schema as it existed on 2026-09-30.
--
-- Generated from a fresh `initialize_db()` build that a table-by-table audit showed to be
-- identical (columns, types, defaults, foreign keys, indexes) to the live database.
-- It folds in everything the retired SCHEMA_EVOLUTIONS list added (investment.sector /
-- industry / last_deep_analysis_at, projection_version.source / last_grok_sweep /
-- catalyst_updates_json, trade_log_entry.tv_order_id).
--
-- IMMUTABLE once applied: schema_migrator records a checksum and refuses to run if this
-- file changes. Change the schema by adding 0002, 0003, ... never by editing this file.
-- Only py_services/domain_model/schema_migrator.py applies these files.

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

CREATE TABLE investment (
        investment_id              TEXT PRIMARY KEY,
        symbol                      TEXT NOT NULL,
        name                        TEXT,
        sector                      TEXT,
        industry                    TEXT,
        asset_class                 TEXT NOT NULL,
        currency                    TEXT NOT NULL DEFAULT 'USD',
        lifecycle_status            TEXT,
        target_weight               REAL,
        target_action               TEXT,
        standing_decision_type      TEXT,
        standing_decision_reason    TEXT,
        standing_decision_source    TEXT,
        standing_decision_review    TEXT,
        pillar_id                   TEXT REFERENCES strategy_pillar(pillar_id),
        sub_strategy_id             TEXT REFERENCES sub_strategy(sub_strategy_id),
        thesis_for_inclusion        TEXT,
        agent_rationale             TEXT,
        is_watchlisted              INTEGER NOT NULL DEFAULT 0,
        watchlist_added_at          TEXT,
        latest_projection_id        TEXT REFERENCES projection_version(projection_id),
        latest_research_event_id    TEXT,
        thesis_breaker_status       TEXT,
        last_deep_analysis_at       TEXT,
        updated_at                  TEXT NOT NULL,
        UNIQUE(symbol)
    );

CREATE TABLE investment_price (
        investment_id   TEXT PRIMARY KEY REFERENCES investment(investment_id),
        price           REAL NOT NULL,
        currency        TEXT NOT NULL DEFAULT 'USD',
        fetched_at      TEXT NOT NULL
    );

CREATE TABLE account_investment (
        account_investment_id   TEXT PRIMARY KEY,
        account_id              TEXT NOT NULL REFERENCES account(account_id),
        investment_id           TEXT NOT NULL REFERENCES investment(investment_id),
        quantity                REAL NOT NULL DEFAULT 0,
        average_cost            REAL,
        book_value              REAL,
        currency                TEXT NOT NULL DEFAULT 'USD',
        last_synced_at          TEXT NOT NULL,
        UNIQUE(account_id, investment_id)
    );

CREATE TABLE price_level_set (
        price_level_set_id  TEXT PRIMARY KEY,
        investment_id       TEXT NOT NULL REFERENCES investment(investment_id),
        schema_version      TEXT,
        last_updated        TEXT,
        last_updated_by     TEXT,
        note                TEXT
    );

CREATE TABLE price_level_tier (
        tier_id              TEXT PRIMARY KEY,
        price_level_set_id   TEXT NOT NULL REFERENCES price_level_set(price_level_set_id),
        tier_kind            TEXT NOT NULL DEFAULT 'BUY_TIER',
        tier_number          INTEGER NOT NULL,
        price                REAL,
        action               TEXT,
        trim_pct             REAL,
        order_type           TEXT,
        basis                TEXT,
        source               TEXT,
        source_date          TEXT,
        condition            TEXT,
        status               TEXT
    );

CREATE TABLE alert (
        alert_id        TEXT PRIMARY KEY,
        investment_id   TEXT REFERENCES investment(investment_id),
        alert_type      TEXT,
        message         TEXT,
        price           REAL,
        condition_json  TEXT,
        active          INTEGER NOT NULL DEFAULT 1,
        resolution      TEXT,
        created_at      TEXT,
        last_fired_at   TEXT,
        expiration_at   TEXT,
        synced_at       TEXT NOT NULL
    );

CREATE TABLE investment_note (
        note_id         TEXT PRIMARY KEY,
        investment_id   TEXT NOT NULL REFERENCES investment(investment_id),
        note_date       TEXT NOT NULL,
        note_type       TEXT,
        body            TEXT NOT NULL,
        source          TEXT
    );

CREATE TABLE projection_version (
        projection_id         TEXT PRIMARY KEY,
        investment_id         TEXT NOT NULL REFERENCES investment(investment_id),
        version               INTEGER NOT NULL,
        saved_at              TEXT NOT NULL,
        analyzed_at           TEXT,
        model                 TEXT,
        fair_value            REAL,
        action                TEXT,
        rationale             TEXT,
        research_event_id     TEXT,
        snapshot_json         TEXT,
        analytics_log_json    TEXT,
        raw_json               TEXT,
        legacy_id               TEXT,
        source                   TEXT,
        last_grok_sweep          TEXT,
        catalyst_updates_json    TEXT,
        UNIQUE(investment_id, version)
    );

CREATE TABLE projection_scenario (
        scenario_id         TEXT PRIMARY KEY,
        projection_id       TEXT NOT NULL REFERENCES projection_version(projection_id),
        scenario_name       TEXT NOT NULL,
        weight              REAL,
        growth_rate         REAL,
        net_margin          REAL,
        exit_pe             REAL,
        quality_multiplier  REAL,
        share_change        REAL,
        rationale           TEXT,
        moat_score          INTEGER,
        management_score    INTEGER,
        year5_revenue       REAL,
        year5_net_income    REAL,
        year5_eps           REAL,
        scenario_price      REAL,
        risks_json          TEXT,
        UNIQUE(projection_id, scenario_name)
    );

CREATE TABLE trade_log_entry (
        entry_id        TEXT PRIMARY KEY,
        investment_id   TEXT NOT NULL REFERENCES investment(investment_id),
        account_id      TEXT REFERENCES account(account_id),
        action          TEXT,
        shares          REAL,
        price           REAL,
        total_cost      REAL,
        order_type      TEXT,
        limit_price     REAL,
        trade_date      TEXT,
        notes           TEXT,
        status          TEXT,
        source          TEXT,
        priority        TEXT,
        logged_at       TEXT,
        tv_order_id     TEXT
    );

CREATE TABLE order_execution (
        execution_id      TEXT PRIMARY KEY,
        executed_at       TEXT NOT NULL,
        investment_id     TEXT NOT NULL REFERENCES investment(investment_id),
        side              TEXT,
        shares            REAL,
        price             REAL,
        decision          TEXT,
        gate_result_json  TEXT
    );

CREATE TABLE cash_flow (
        flow_id                             TEXT PRIMARY KEY,
        flow_date                           TEXT,
        flow_type                           TEXT,
        amount_cad                          REAL,
        portfolio_value_before_flow_cad      REAL,
        account                              TEXT
    );

CREATE TABLE cash_flow_baseline (
        account                TEXT PRIMARY KEY,
        starting_balance_cad   REAL,
        starting_date          TEXT
    );

CREATE TABLE portfolio_policy (
        policy_id                                TEXT PRIMARY KEY,
        rebalance_frequency                      TEXT,
        portfolio_value_usd_target               REAL,
        max_marginal_risk_contribution_pct        REAL,
        max_cluster_variance_contribution_pct      REAL,
        rebalance_band_relative_pct                REAL,
        rebalance_band_absolute_pct                REAL,
        rebalance_band_critical_multiplier          REAL,
        account_preference_rules_json                TEXT,
        psu_funding_rule_json                          TEXT,
        updated_at                                      TEXT NOT NULL
    );

CREATE TABLE portfolio_change_log (
        entry_id        TEXT PRIMARY KEY,
        version         TEXT NOT NULL,
        entry_date      TEXT NOT NULL,
        note            TEXT NOT NULL,
        created_at      TEXT NOT NULL
    );

CREATE TABLE broker_exchange_rate (
        id              INTEGER PRIMARY KEY CHECK (id = 1),
        usd_to_cad_rate REAL NOT NULL,
        synced_at       TEXT NOT NULL
    );

CREATE TABLE broker_reported_total (
        id              INTEGER PRIMARY KEY CHECK (id = 1),
        total_usd       REAL NOT NULL,
        total_cad       REAL,
        synced_at       TEXT NOT NULL,
        source          TEXT
    );

CREATE INDEX idx_alert_investment ON alert(investment_id);

CREATE INDEX idx_investment_note_investment ON investment_note(investment_id, note_date);

CREATE INDEX idx_investment_pillar ON investment(pillar_id);

CREATE INDEX idx_investment_lifecycle ON investment(lifecycle_status);

CREATE INDEX idx_account_investment_account ON account_investment(account_id);

CREATE INDEX idx_account_investment_investment ON account_investment(investment_id);

CREATE INDEX idx_projection_investment ON projection_version(investment_id);

CREATE INDEX idx_projection_scenario_projection ON projection_scenario(projection_id);

