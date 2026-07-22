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
 * Scope (Wave 2 Task 9.4 write side + Task 10/11 read-path cutover):
 *   `setWatchlisted()` (write) plus `getInvestment()`, `listThesisHoldings()`,
 *   `listWatchlisted()`, and `listPillars()` (reads) are exposed today. Fields
 *   verified byte-identical against `data/theses/target-portfolio.json` for all
 *   75 thesis holdings before this cutover: `role`->`lifecycle_status`,
 *   `targetWeight`->`target_weight`, `pillarId`->`pillar_id`,
 *   `subStrategyId`->`sub_strategy_id`, `thesisForInclusion`->`thesis_for_inclusion`,
 *   `agentRationale`->`agent_rationale`. Fields NOT ported because the source
 *   JSON document carries no SQLite equivalent (globalSettings, changeLog,
 *   schemaVersion, per-holding `shares`, structured `thesisBreakers`/
 *   `standingDecision` sub-objects beyond the 4 flat `standing_decision_*`
 *   scalar columns) are intentionally left on the full-document JSON read path
 *   in `ThesisService.getThesis()` — see that file's module docstring.
 *
 * Key Functions (Index):
 *   - resolveInvestmentId(symbol) - Idempotent lookup-or-insert, mirrors
 *     investment_repository.py::resolve_investment
 *   - getInvestment(symbol) - Full row lookup by symbol
 *   - setWatchlisted(symbol, isWatchlisted, watchlistAddedAt) - Updates
 *     is_watchlisted/watchlist_added_at, mirrors
 *     investment_repository.py::update_investment_fields
 *   - listThesisHoldings() - All investments with a non-null target_weight,
 *     mapped to the JSON holding shape (ticker/name/pillarId/subStrategyId/
 *     role/targetWeight/thesisForInclusion/agentRationale)
 *   - listWatchlisted() - All investments with is_watchlisted=1, mapped to
 *     {ticker, addedAt}
 *   - listPillars() - All strategy_pillar rows, mapped to {id, name, targetWeight}
 */
import Database from 'better-sqlite3';

export interface ThesisHoldingView {
    ticker: string;
    name: string | null;
    pillarId: string | null;
    subStrategyId: string | null;
    role: string | null;
    targetWeight: number | null;
    thesisForInclusion: string | null;
    agentRationale: string | null;
}

export interface WatchlistItemView {
    ticker: string;
    addedAt: string;
}

export interface PillarView {
    id: string;
    name: string;
    targetWeight: number | null;
}

export interface InvestmentRow {
    investment_id: string;
    symbol: string;
    name: string | null;
    sector: string | null;
    industry: string | null;
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
                latest_projection_id        TEXT,
                latest_research_event_id    TEXT,
                thesis_breaker_status       TEXT,
                updated_at                  TEXT NOT NULL,
                UNIQUE(symbol)
            );

            CREATE INDEX IF NOT EXISTS idx_investment_pillar ON investment(pillar_id);
            CREATE INDEX IF NOT EXISTS idx_investment_lifecycle ON investment(lifecycle_status);
        `);
        // Deliberately NO ALTER TABLE here — merely opening this repository against
        // the real, pre-completion domain_model.sqlite must never mutate its
        // schema (respecting this class's "never ALTER the real file on open"
        // rule and CLAUDE.md's don't-mutate-gitignored-data rule). Fresh test DBs
        // get sector/industry from the CREATE TABLE above; the real file's two new
        // columns are added by db_client.py::_evolve_schema (Python, on any
        // initialize_db call) OR, failing that, lazily at first write by
        // updateSectorIndustry() below — never on a read-only open.
    }

    /** Mirrors `investment_repository.py::update_investment_sector` — persist the
     * yfinance/SECTOR_OVERRIDES-resolved sector/industry for a symbol (Wave 3
     * completion). Resolves (creating if new) the investment row first, so a
     * symbol seen only via a price refresh still gets its metadata. This is the
     * only TS write path for these two columns, per the "one writer per table"
     * rule. Lazily self-heals the two columns on the real file at first write
     * (a genuine write path, never a read-only open) so a pre-completion file
     * that Python's _evolve_schema hasn't reached yet still accepts the write. */
    updateSectorIndustry(symbol: string, sector: string | null, industry: string | null): void {
        const cols = new Set(
            (this.db.prepare('PRAGMA table_info(investment)').all() as Array<{ name: string }>).map(c => c.name)
        );
        if (!cols.has('sector')) this.db.exec('ALTER TABLE investment ADD COLUMN sector TEXT');
        if (!cols.has('industry')) this.db.exec('ALTER TABLE investment ADD COLUMN industry TEXT');
        const investmentId = this.resolveInvestmentId(symbol);
        const now = new Date().toISOString();
        this.db
            .prepare(
                `UPDATE investment SET sector = ?, industry = ?, updated_at = ? WHERE investment_id = ?`
            )
            .run(sector, industry, now, investmentId);
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

    /** Mirrors the `holdings` array shape of `data/theses/target-portfolio.json`
     * (read side, Wave 2 Task 10/11). Only rows with a non-null `target_weight`
     * are thesis holdings — verified 1:1 against the 75 holdings in the JSON
     * source (see module docstring). `role` maps from `lifecycle_status`
     * (verified identical for every holding), NOT `target_action` (a distinct,
     * largely-null DCF-signal column). */
    listThesisHoldings(): ThesisHoldingView[] {
        const rows = this.db
            .prepare(
                `SELECT symbol, name, pillar_id, sub_strategy_id, lifecycle_status,
                        target_weight, thesis_for_inclusion, agent_rationale
                 FROM investment
                 WHERE target_weight IS NOT NULL
                 ORDER BY symbol`
            )
            .all() as Array<{
                symbol: string; name: string | null; pillar_id: string | null;
                sub_strategy_id: string | null; lifecycle_status: string | null;
                target_weight: number | null; thesis_for_inclusion: string | null;
                agent_rationale: string | null;
            }>;
        return rows.map(r => ({
            ticker: r.symbol,
            name: r.name,
            pillarId: r.pillar_id,
            subStrategyId: r.sub_strategy_id,
            role: r.lifecycle_status,
            targetWeight: r.target_weight,
            thesisForInclusion: r.thesis_for_inclusion,
            agentRationale: r.agent_rationale,
        }));
    }

    /** Mirrors the shape of `data/watchlist.json`'s `watchlist` array (read
     * side, Wave 2 Task 10/11). Verified byte-identical ticker set and
     * `addedAt`/`watchlist_added_at` timestamps against the JSON file before
     * this cutover. */
    listWatchlisted(): WatchlistItemView[] {
        const rows = this.db
            .prepare(
                `SELECT symbol, watchlist_added_at
                 FROM investment
                 WHERE is_watchlisted = 1
                 ORDER BY watchlist_added_at`
            )
            .all() as Array<{ symbol: string; watchlist_added_at: string | null }>;
        return rows.map(r => ({ ticker: r.symbol, addedAt: r.watchlist_added_at ?? '' }));
    }

    /** Mirrors `data/theses/target-portfolio.json`'s `pillars` array (read
     * side, Wave 2 Task 10/11). `strategy_pillar` carries only
     * (pillar_id, name, target_weight) — verified an exact 1:1 field match
     * against all 13 pillars in the JSON source, no bandConfig/other pillar
     * metadata exists in either place. */
    listPillars(): PillarView[] {
        const rows = this.db
            .prepare(`SELECT pillar_id, name, target_weight FROM strategy_pillar ORDER BY pillar_id`)
            .all() as Array<{ pillar_id: string; name: string; target_weight: number | null }>;
        return rows.map(r => ({ id: r.pillar_id, name: r.name, targetWeight: r.target_weight }));
    }
}
