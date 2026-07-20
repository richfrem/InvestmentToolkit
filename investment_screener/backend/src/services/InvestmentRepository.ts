/**
 * InvestmentRepository.ts - SQLite persistence for the shared `investment` table.
 *
 * Purpose:
 *   TS-side counterpart to `py_services/domain_model/investment_repository.py`
 *   (ADR-029), reading/writing the same physical `data/domain_model.sqlite` file
 *   via `better-sqlite3`. Mirrors `ProjectionRepository.ts`'s established Wave 1
 *   pattern (Wave 2 Task 9.4 investigation): a thin repository class wrapping the
 *   Node SQLite driver for one table, with `ensureSchema()` transcribing the same
 *   `CREATE TABLE IF NOT EXISTS` DDL as `db_client.py::initialize_db` (idempotent
 *   no-op against the real file; load-bearing for fresh temp/test databases).
 *   No script or service should open its own connection against `investment` —
 *   this is the only place that does, per this migration's global constraint.
 *
 * Layer:
 *   Backend / Services / Data Persistence (SQLite-backed repository)
 *
 * Scope (Wave 2 Task 9.4):
 *   Only the fields `WatchlistService.ts`'s write side needs
 *   (`is_watchlisted`, `watchlist_added_at`) are exposed today via
 *   `setWatchlisted()`. This intentionally does NOT attempt a full port of every
 *   `update_investment_fields()` column — that is a separate consumer-cutover
 *   concern (Task 10/11) requiring its own read-path investigation per field.
 *
 * Key Functions (Index):
 *   - resolveInvestmentId(symbol) - Idempotent lookup-or-insert, mirrors
 *     investment_repository.py::resolve_investment
 *   - getInvestment(symbol) - Full row lookup by symbol
 *   - setWatchlisted(symbol, isWatchlisted, watchlistAddedAt) - Updates
 *     is_watchlisted/watchlist_added_at, mirrors
 *     investment_repository.py::update_investment_fields
 */
import Database from 'better-sqlite3';

export interface InvestmentRow {
    investment_id: string;
    symbol: string;
    name: string | null;
    asset_class: string;
    currency: string;
    lifecycle_status: string | null;
    target_weight: number | null;
    target_action: string | null;
    standing_decision_type: string | null;
    standing_decision_reason: string | null;
    standing_decision_source: string | null;
    standing_decision_review: string | null;
    pillar_id: string | null;
    sub_strategy_id: string | null;
    thesis_for_inclusion: string | null;
    agent_rationale: string | null;
    is_watchlisted: number;
    watchlist_added_at: string | null;
    latest_projection_id: string | null;
    latest_research_event_id: string | null;
    thesis_breaker_status: string | null;
    updated_at: string;
}

export class InvestmentRepository {
    private db: Database.Database;

    constructor(dbPath: string) {
        this.db = new Database(dbPath);
        this.ensureSchema();
    }

    close(): void {
        this.db.close();
    }

    /** Transcribed from `py_services/domain_model/db_client.py::initialize_db` —
     * see `ProjectionRepository.ts`'s module docstring for the sync contract this
     * mirrors. Idempotent against the real, already-initialized file; never runs
     * `ALTER TABLE` against it. */
    private ensureSchema(): void {
        this.db.pragma('journal_mode = WAL');
        this.db.pragma('foreign_keys = ON');

        this.db.exec(`
            CREATE TABLE IF NOT EXISTS strategy_pillar (
                pillar_id       TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                target_weight   REAL
            );

            CREATE TABLE IF NOT EXISTS sub_strategy (
                sub_strategy_id TEXT PRIMARY KEY,
                pillar_id       TEXT REFERENCES strategy_pillar(pillar_id),
                name            TEXT NOT NULL
            );

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
                latest_projection_id        TEXT,
                latest_research_event_id    TEXT,
                thesis_breaker_status       TEXT,
                updated_at                  TEXT NOT NULL,
                UNIQUE(symbol)
            );

            CREATE INDEX IF NOT EXISTS idx_investment_pillar ON investment(pillar_id);
            CREATE INDEX IF NOT EXISTS idx_investment_lifecycle ON investment(lifecycle_status);
        `);
    }

    /** Mirrors `investment_repository.py::resolve_investment` — idempotent
     * lookup-or-insert of the `investment` row for a symbol, returning its
     * `investment_id`. Calling twice for the same symbol never inserts a
     * duplicate row. */
    resolveInvestmentId(symbol: string, assetClass = 'EQUITY', currency = 'USD'): string {
        const existing = this.db
            .prepare('SELECT investment_id FROM investment WHERE symbol = ?')
            .get(symbol) as { investment_id: string } | undefined;
        if (existing) return existing.investment_id;

        const investmentId = symbol.toUpperCase();
        const now = new Date().toISOString();
        this.db
            .prepare(
                `INSERT INTO investment (investment_id, symbol, name, asset_class, currency, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?)`
            )
            .run(investmentId, symbol, symbol, assetClass, currency, now);
        return investmentId;
    }

    /** Mirrors `investment_repository.py::get_investment`, looked up by symbol
     * (the caller-facing key everywhere else in this codebase uses `ticker`,
     * never the internal `investment_id`). */
    getInvestment(symbol: string): InvestmentRow | null {
        const row = this.db
            .prepare('SELECT * FROM investment WHERE symbol = ?')
            .get(symbol) as InvestmentRow | undefined;
        return row ?? null;
    }

    /** Mirrors `investment_repository.py::update_investment_fields(is_watchlisted=...,
     * watchlist_added_at=...)`. Resolves (creating if new) the investment row for
     * `symbol` first, so watchlisting a ticker with no prior `investment` row
     * (e.g. a pure watchlist candidate never held or projected) still succeeds. */
    setWatchlisted(symbol: string, isWatchlisted: boolean, watchlistAddedAt: string | null): void {
        const investmentId = this.resolveInvestmentId(symbol);
        const now = new Date().toISOString();
        this.db
            .prepare(
                `UPDATE investment
                 SET is_watchlisted = ?, watchlist_added_at = ?, updated_at = ?
                 WHERE investment_id = ?`
            )
            .run(isWatchlisted ? 1 : 0, watchlistAddedAt, now, investmentId);
    }
}
