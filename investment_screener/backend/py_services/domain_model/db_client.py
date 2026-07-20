# DDL drift check (performed at authoring time, re-run whenever this file changes):
# Source: docs/architecture/domain-data-model.md (account, strategy_pillar, sub_strategy,
#   investment, investment_price, account_investment, price_level_set, price_level_tier,
#   alert, investment_note, projection_version, projection_scenario, portfolio_policy)
#   + docs/architecture/supplementary-domain-schemas.md (trade_log_entry, order_execution,
#   cash_flow, cash_flow_baseline).
#
# Method: every column/type/constraint below was diffed, table by table, against the
# "v3 Column-Level Schema" SQL block (domain-data-model.md lines ~305-475), the `alert` and
# `investment_note` CREATE TABLE blocks in the same file's "Response to Review" section, and the
# markdown column tables for trade_log_entry/order_execution/cash_flow/cash_flow_baseline in
# supplementary-domain-schemas.md (Domain 2, 3, 4 section).
#
# Deviations from source documents (must be empty, or each entry must be justified):
#   - projection_version.research_event_id: source docs show this as
#     "REFERENCES intelligence_event(event_id)" but that table lives in a different SQLite
#     file (intelligence.sqlite) than this one (domain_model's own .sqlite) — SQLite cannot
#     enforce a cross-database FK, so this column is declared without a REFERENCES clause here.
#     Referential integrity for this link is enforced at the repository layer (Wave 1's
#     projection repository must validate the event_id exists before insert), not by SQLite.
#     Same reasoning applies to investment.latest_research_event_id.
#   - trade_log_entry.account_id: supplementary-domain-schemas.md's own column table for
#     trade_log_entry (Domain 2, 3, 4 section) literally lists this as a plain `account` TEXT
#     field ("e.g. TFSA, RRSP") with no FK notation. This file instead names/types it
#     `account_id TEXT REFERENCES account(account_id)`. That choice is not arbitrary — it matches
#     domain-data-model.md's v3 Mermaid ERD, which shows `TRADE_LOG_ENTRY { TEXT account_id FK }`
#     and an explicit `ACCOUNT ||--o{ TRADE_LOG_ENTRY : "logged against"` relationship. The two
#     named source documents disagree with each other on this one column; this file follows the
#     newer, FK-relationship-bearing domain-data-model.md version rather than the older plain-text
#     column table in supplementary-domain-schemas.md. Flagged so a reviewer can confirm that
#     choice, not silently pick a side.
#   - cash_flow.account: for contrast, this column was left as plain `account TEXT` with no
#     rename/FK, even though domain-data-model.md's v3 Mermaid ERD shows the same
#     `TEXT account_id FK` treatment for CASH_FLOW that it shows for TRADE_LOG_ENTRY. This file's
#     cash_flow DDL instead matches supplementary-domain-schemas.md's plain `account` column
#     table verbatim. Net effect: the "does `account` get promoted to `account_id` with a real
#     FK" question was answered inconsistently between these two tables — trade_log_entry says
#     yes, cash_flow says no — even though both source documents show the exact same ambiguity
#     for both tables. Not fixed here (Task 1 is schema transcription, not schema redesign);
#     flagged for a follow-up decision before Wave 1's portfolio-ledger repository work assumes
#     one behavior or the other.
#   - portfolio_policy: Step 3 of this task's brief cites this table's DDL as coming from
#     "domain-data-model.md § Missing top-level PORTFOLIO/config entity" — that section heading
#     does not exist anywhere in domain-data-model.md (checked: the file's full heading list has
#     no "PORTFOLIO" or "policy" section at all). The DDL is schema-consistent with
#     docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md §2.14
#     ("Account/portfolio policy" — same five numeric caps/bands, same two JSON rule-blob
#     columns), but that spec file is not one of the two files this task names as the DDL source,
#     and it does not itself spell out exact column names (`policy_id`, `rebalance_frequency`,
#     etc.) — those exact names only appear pre-written in this task's own implementation plan
#     document. This is a citation-accuracy issue (the brief points at a document section that
#     isn't there), not a schema-content issue — the columns below are internally consistent with
#     every real design document that discusses `portfolio_policy`, just not literally
#     "transcribed verbatim" from either of the two files named for that purpose in Step 3.
#   - projection_version.raw_json / projection_version.legacy_id: not present in the
#     source design documents. Added post-hoc (Wave 1 Task 5 review fix) so this file
#     stays the single source of truth for the shared schema — these two nullable
#     columns previously existed ONLY as a runtime `ALTER TABLE` issued by
#     `ProjectionRepository.ts`'s constructor against the real, shared
#     `domain_model.sqlite` file, which is what let a TypeScript import silently mutate
#     production schema outside this module. `raw_json` holds the full validated
#     `Projection` object (round-trip fidelity for `.passthrough()` fields the
#     structured columns don't model); `legacy_id` holds the original Zod `Projection.id`
#     UUID used to group version rows by projection identity. See ProjectionRepository.ts
#     module docstring for the full design rationale.
#   - projection_version.source / last_grok_sweep / catalyst_updates_json: not present in
#     the source design documents. Added post-hoc (Wave 1 Task 6, apply_catalyst.py
#     rewire) after a real-data investigation found `projection_version` had no way to
#     represent the JSON model's `entry.source` (`AI_AGENT`/`USER`/`SYSTEM`/`ETF_ANALYSIS`),
#     `entry.lastGrokSweep`, or `entry.catalystUpdates` fields — all three are read/written
#     by `apply_catalyst.py` and are real, present data (19/132 and 18/132 real
#     `projections/*.json` entries carry `lastGrokSweep`/`catalystUpdates` respectively; 8
#     of 82 real tickers have zero `AI_AGENT`-sourced entries, only `ETF_ANALYSIS`). Without
#     `source`, `apply_catalyst.py`'s `_find_latest_ai_agent` (source-filtered, latest by
#     `savedAt`) has no SQL equivalent — `get_latest_projection`'s `MAX(version)` alone
#     silently picks a non-`AI_AGENT` row for those 8 tickers and, separately, a
#     stale/wrong-source row for 3 more real tickers whose version numbers are not
#     chronological (`BW`, `CLSK`, `LITE` — confirmed by direct comparison against real
#     `projections/*.json`). `last_grok_sweep`/`catalyst_updates_json` are added so
#     `--record-sweep` and the catalyst-apply write path have somewhere to persist their
#     stamped date / appended catalyst-log entries, matching the JSON model's fields
#     one-for-one. `migrate_projections_to_sqlite.py` is updated to populate all three for
#     future migration runs; the real file's 115 already-migrated rows predate this change
#     and have `NULL` in all three columns until a follow-up backfill re-migration is run
#     (out of scope for Task 6 — flagged for the reviewer, not silently assumed backfilled).
#   - (no other deviations found as of this transcription)
import sqlite3


def initialize_db(db_path: str) -> sqlite3.Connection:
    """Open (creating if absent) the v3.2 domain-model SQLite database.

    Mirrors ``py_services/intelligence/db_client.py::initialize_db``'s calling
    convention: WAL mode, foreign keys on, idempotent schema creation.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS account (
        account_id      TEXT PRIMARY KEY,
        account_name    TEXT NOT NULL,
        account_type    TEXT,
        base_currency   TEXT NOT NULL DEFAULT 'CAD'
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS strategy_pillar (
        pillar_id       TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        target_weight   REAL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS sub_strategy (
        sub_strategy_id TEXT PRIMARY KEY,
        pillar_id       TEXT REFERENCES strategy_pillar(pillar_id),
        name            TEXT NOT NULL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS investment (
        investment_id              TEXT PRIMARY KEY,
        symbol                      TEXT NOT NULL,
        name                        TEXT,
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
        updated_at                  TEXT NOT NULL,
        UNIQUE(symbol)
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS investment_price (
        investment_id   TEXT PRIMARY KEY REFERENCES investment(investment_id),
        price           REAL NOT NULL,
        currency        TEXT NOT NULL DEFAULT 'USD',
        fetched_at      TEXT NOT NULL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS account_investment (
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
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS price_level_set (
        price_level_set_id  TEXT PRIMARY KEY,
        investment_id       TEXT NOT NULL REFERENCES investment(investment_id),
        schema_version      TEXT,
        last_updated        TEXT,
        last_updated_by     TEXT,
        note                TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS price_level_tier (
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
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS alert (
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
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_investment ON alert(investment_id);")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS investment_note (
        note_id         TEXT PRIMARY KEY,
        investment_id   TEXT NOT NULL REFERENCES investment(investment_id),
        note_date       TEXT NOT NULL,
        note_type       TEXT,
        body            TEXT NOT NULL,
        source          TEXT
    );
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_investment_note_investment "
        "ON investment_note(investment_id, note_date);"
    )

    conn.execute("""
    CREATE TABLE IF NOT EXISTS projection_version (
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
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS projection_scenario (
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
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS trade_log_entry (
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
        logged_at       TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS order_execution (
        execution_id      TEXT PRIMARY KEY,
        executed_at       TEXT NOT NULL,
        investment_id     TEXT NOT NULL REFERENCES investment(investment_id),
        side              TEXT,
        shares            REAL,
        price             REAL,
        decision          TEXT,
        gate_result_json  TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS cash_flow (
        flow_id                             TEXT PRIMARY KEY,
        flow_date                           TEXT,
        flow_type                           TEXT,
        amount_cad                          REAL,
        portfolio_value_before_flow_cad      REAL,
        account                              TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS cash_flow_baseline (
        account                TEXT PRIMARY KEY,
        starting_balance_cad   REAL,
        starting_date          TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_policy (
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
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_investment_pillar ON investment(pillar_id);")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_investment_lifecycle ON investment(lifecycle_status);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_investment_account "
        "ON account_investment(account_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_investment_investment "
        "ON account_investment(investment_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projection_investment "
        "ON projection_version(investment_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projection_scenario_projection "
        "ON projection_scenario(projection_id);"
    )

    conn.commit()
    return conn
