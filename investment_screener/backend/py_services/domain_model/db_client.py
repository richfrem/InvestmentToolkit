# ---------------------------------------------------------------------------------------
# NOTE (schema migrations): the DDL this header documents no longer lives in this file.
# It is `investment_screener/backend/schema/domain_model/0001_baseline.sql`, applied by
# `schema_migrator.migrate()`, which is the only code allowed to create or alter tables.
# Change the schema by adding the next numbered migration, never by editing this file or
# any applied migration. The deviations recorded below remain accurate history.
# ---------------------------------------------------------------------------------------
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
#     future migration runs. CORRECTION (Wave 1 Task 6 follow-up fix): the original note
#     here claimed the real file's 115 already-migrated rows "have NULL in these columns"
#     — that was wrong. `CREATE TABLE IF NOT EXISTS` is a no-op against a table that
#     already exists, so the three columns did not exist in the real file's schema at
#     all (verified via `PRAGMA table_info`/`.schema projection_version`), not merely
#     NULL-valued. Fixed via the schema self-heal in `_evolve_schema`/`SCHEMA_EVOLUTIONS`
#     below, which runs an `ALTER TABLE ... ADD COLUMN` for any table+column pair
#     registered there that is missing from an existing file. The real file's `source`
#     column has since been backfilled from `projections/*.json` (see
#     `migrate_projections_to_sqlite.py --backfill-source`); `last_grok_sweep`/
#     `catalyst_updates_json` remain NULL on those 115 pre-existing rows (optional/future
#     backfill, not required for `apply_catalyst.py` to function).
#   - broker_exchange_rate: not present in either named source design document.
#     Added post-hoc (Wave 3 Task 8, CAD exchange-rate gap closure) per an explicit
#     user design decision recorded in ADR-030's "Wave 3 addendum" section. This is
#     the ONE broker-reported fact that cannot be derived from anything else the
#     schema stores: the live USD->CAD FX rate, inferred at sync time from
#     TradingView's own native totalEquityCADCombined/totalEquityUSDCombined ratio
#     (CLAUDE.md pitfall #27 — never an external FX API). It is deliberately a
#     singleton (CHECK(id = 1), one row ever, overwritten each sync), NOT a
#     per-account or historical table — mirroring investment_price's "store this one
#     broker fact, don't invent history we don't need" shape. CAD-denominated totals
#     are explicitly NOT stored: every CAD figure is computed as usd_value * rate at
#     read time, matching ADR-030's "store facts, compute aggregates" principle (the
#     rate is a fact; CAD totals derived from it are aggregates). Both readers —
#     helpers.ts::getLiveUsdCadRate() (TS) and
#     portfolio_repository.py::load_portfolio_state_from_db() (Python) — now read this
#     scalar with a static fallback for a fresh/never-synced DB, closing the
#     retained-JSON gap documented in
#     docs/superpowers/status/wave3-cad-exchange-rate-retained-json.md.
#   - broker_reported_total: not present in either named source design document.
#     Added post-hoc (Wave 3 Task 8, tvSnapshot closure) per an explicit user
#     design decision recorded in ADR-030's "Wave 3 addendum" pattern. This is the
#     broker's OWN last-reported portfolio total (totalUSD, and totalCAD if present)
#     — a broker-reported FACT the schema cannot recompute (same reasoning as
#     broker_exchange_rate above), captured for exactly one consumer:
#     verify_portfolio_total.py's reconciliation/audit check, which compares the
#     broker's reported total against get_portfolio_total_value()'s computed total.
#     This does NOT reverse ADR-030: get_portfolio_total_value() remains the
#     authoritative computed total for everything else; this scalar is stored only
#     as the reconciliation comparison SOURCE (the audited-against figure), not as
#     "the" total. Singleton (CHECK(id = 1), one row ever, overwritten each sync),
#     mirroring broker_exchange_rate's "store this one broker fact" shape. `source`
#     holds the totals.totalSource value the now-retired portfolio.json used to carry
#     (e.g. "tv_authoritative"); broker syncs now write it here directly.
#   - investment.sector / investment.industry: not present in either named source
#     design document. Added post-hoc (Wave 3 completion, last-portfolio.json-write
#     closure) per an explicit user design decision. sector/industry are the only
#     enriched holding-display facts GET /api/portfolio needed from the then-current
#     portfolio.json (retired since) that the schema did not already carry (name and pillar_id were added in
#     Wave 0/2). They are resolved by the SAME real code path that resolves them
#     today — fetch_portfolio_heatmap.py's yfinance info.get("sector")/("industry")
#     lookup (with SECTOR_OVERRIDES) during a /refresh-prices call — and persisted
#     alongside the fresh price into investment via update_investment_sector(). Both
#     are nullable TEXT (a freshly TV-synced-but-not-yet-price-refreshed investment
#     has no resolved sector yet; readers fall back to "Unknown", matching
#     fetch_portfolio_heatmap.py's own fallback). Registered in SCHEMA_EVOLUTIONS so
#     the real, already-existing domain_model.sqlite self-heals these two columns.
#   - (no other deviations found as of this transcription)
"""db_client.py - Open the domain-model SQLite database at its newest schema.

Purpose:
    Single entry point for opening investment_screener/backend/data/domain_model.sqlite
    (the sole source of truth for holdings, accounts, prices, theses and trades; the
    JSON files that preceded it are retired). Opens in WAL mode with foreign keys on and
    delegates all table creation and change to schema_migrator.migrate. The comment
    block above records where the schema deviates from its source design documents.

Layer:
    Backend / Python Services / Domain Model

Usage Examples:
    from domain_model.db_client import initialize_db
    conn = initialize_db("investment_screener/backend/data/domain_model.sqlite")

Key Functions (Index):
    - initialize_db(): open (creating if absent) the database at its newest schema

Key Input Dependencies:
    - investment_screener/backend/schema/domain_model/*.sql (numbered migrations, via schema_migrator)

Key Output Dependencies:
    - The sqlite3 connection every domain_model repository takes as its first argument
"""
import sqlite3

from .schema_migrator import migrate


def initialize_db(db_path: str) -> sqlite3.Connection:
    """Open (creating if absent) the domain-model SQLite database at its newest schema.

    Mirrors ``py_services/intelligence/db_client.py::initialize_db``'s calling
    convention: WAL mode, foreign keys on, idempotent. Table creation and changes are
    delegated entirely to ``schema_migrator.migrate`` (numbered SQL files, ledger table,
    pre-migration backup of a populated file).
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    migrate(conn, db_path=db_path)
    conn.commit()
    return conn
