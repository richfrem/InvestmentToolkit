/**
 * InvestmentRepository.ts - SQLite persistence for the shared `investment` table.
 *
 * Purpose:
 *   TS-side counterpart to `py_services/domain_model/investment_repository.py`
 *   (ADR-029), reading/writing the same physical `data/domain_model.sqlite` file
 *   via `better-sqlite3`. Mirrors `ProjectionRepository.ts`'s established Wave 1
 *   pattern (Wave 2 Task 9.4 investigation): a thin repository class wrapping the
 *   Node SQLite driver for one table, with `ensureSchema()` verifying the Python-owned schema version
 *   (`utils/schemaVersion.ts`); Node never creates or alters tables.
 *   No script or service should open its own connection against `investment` —
 *   this is the only place that does, per this migration's global constraint.
 *
 * Layer:
 *   Backend / Services / Data Persistence (SQLite-backed repository)
 *
 * Scope:
 *   `setWatchlisted()` and `updateThesisFields()` (writes) plus `getInvestment()`,
 *   `listThesisHoldings()`, `listWatchlisted()`, and `listPillars()` (reads).
 *   Thesis holding fields map `role`->`lifecycle_status`, `targetWeight`->`target_weight`,
 *   `pillarId`->`pillar_id`, `subStrategyId`->`sub_strategy_id`,
 *   `thesisForInclusion`->`thesis_for_inclusion`, `agentRationale`->`agent_rationale`.
 *   Thesis breakers live in `thesis_breaker` (ThesisBreakerRepository) and are attached
 *   by `ThesisService.getThesis()`.
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
 *   - listDocumentMembers() - thesis_document_member rows as {symbol: [document_id, ...]}
 */
import Database from 'better-sqlite3';
import { ensureSchemaReady } from '../utils/schemaVersion';

export interface ThesisHoldingView {
    ticker: string;
    name: string | null;
    assetClass?: string | null;
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
        this.ensureSchema(dbPath);
    }

    close(): void {
        this.db.close();
    }

    /** Connection settings only. The schema itself is owned by Python (see
     * `utils/schemaVersion.ts`): this verifies the version and never creates or
     * alters a table. */
    private ensureSchema(dbPath: string): void {
        this.db.pragma('journal_mode = WAL');
        this.db.pragma('foreign_keys = ON');
        ensureSchemaReady(this.db, dbPath);
    }

    /** Mirrors `investment_repository.py::update_investment_sector` — persist the
     * yfinance/SECTOR_OVERRIDES-resolved sector/industry for a symbol (Wave 3
     * completion). Resolves (creating if new) the investment row first, so a
     * symbol seen only via a price refresh still gets its metadata. This is the
     * only TS write path for these two columns, per the "one writer per table"
     * rule. The two columns are part of the schema baseline (migration 0001), so
     * there is no runtime ALTER here. */
    updateSectorIndustry(symbol: string, sector: string | null, industry: string | null): void {
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

    /** Return the total shares held across all accounts for a symbol. */
    getSharesHeld(symbol: string): number {
        const row = this.db
            .prepare(
                `SELECT SUM(ai.quantity) as total_shares
                 FROM account_investment ai
                 JOIN investment i ON ai.investment_id = i.investment_id
                 WHERE i.symbol = ?`
            )
            .get(symbol) as { total_shares: number | null } | undefined;
        return row?.total_shares ?? 0;
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

    /** Wave 8: writes the thesis-editable fields on one investment row --
     * TS-side counterpart to investment_repository.py::update_investment_fields,
     * used by ThesisService.ts's saveThesis()/updateHolding()/addHolding()/
     * removeHolding()/replaceHoldings() to persist per-holding thesis edits
     * directly into SQLite. */
    updateThesisFields(symbol: string, fields: {
        name?: string | null;
        pillarId?: string | null;
        subStrategyId?: string | null;
        targetWeight?: number | null;
        thesisForInclusion?: string | null;
        agentRationale?: string | null;
        role?: string | null;
    }): void {
        const investmentId = this.resolveInvestmentId(symbol);
        const now = new Date().toISOString();
        const columnMap: Record<string, string> = {
            name: 'name', pillarId: 'pillar_id', subStrategyId: 'sub_strategy_id',
            targetWeight: 'target_weight', thesisForInclusion: 'thesis_for_inclusion',
            agentRationale: 'agent_rationale', role: 'lifecycle_status',
        };
        const setClauses: string[] = [];
        const params: unknown[] = [];
        for (const [key, value] of Object.entries(fields)) {
            if (value === undefined) continue;
            setClauses.push(`${columnMap[key]} = ?`);
            params.push(value);
        }
        if (setClauses.length === 0) return;
        setClauses.push('updated_at = ?');
        params.push(now, investmentId);
        this.db.prepare(`UPDATE investment SET ${setClauses.join(', ')} WHERE investment_id = ?`).run(...params);
    }

    /** Which thesis documents list each stock: {symbol: [document_id, ...]}, both sorted. */
    listDocumentMembers(): Record<string, string[]> {
        const rows = this.db
            .prepare('SELECT symbol, document_id FROM thesis_document_member ORDER BY symbol, document_id')
            .all() as Array<{ symbol: string; document_id: string }>;
        const out: Record<string, string[]> = {};
        for (const r of rows) (out[r.symbol] ??= []).push(r.document_id);
        return out;
    }

    /** The thesis holdings array. Only rows with a non-null `target_weight`
     * are thesis holdings. `role` maps from `lifecycle_status`,
     * NOT `target_action` (a distinct,
     * largely-null DCF-signal column). */
    listThesisHoldings(): ThesisHoldingView[] {
        const rows = this.db
            .prepare(
                `SELECT symbol, name, asset_class, pillar_id, sub_strategy_id, lifecycle_status,
                        target_weight, thesis_for_inclusion, agent_rationale
                 FROM investment
                 WHERE target_weight IS NOT NULL
                 ORDER BY symbol`
            )
            .all() as Array<{
                symbol: string; name: string | null; asset_class: string | null;
                pillar_id: string | null; sub_strategy_id: string | null;
                lifecycle_status: string | null; target_weight: number | null;
                thesis_for_inclusion: string | null; agent_rationale: string | null;
            }>;
        return rows.map(r => ({
            ticker: r.symbol,
            name: r.name,
            assetClass: r.asset_class,
            pillarId: r.pillar_id,
            subStrategyId: r.sub_strategy_id,
            role: r.lifecycle_status,
            targetWeight: r.target_weight,
            thesisForInclusion: r.thesis_for_inclusion,
            agentRationale: r.agent_rationale,
        }));
    }

    /** The watchlist: every investment with `is_watchlisted = 1`, as
     * {ticker, addedAt} from `watchlist_added_at`. */
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

    /** The strategy pillars. `strategy_pillar` carries only
     * (pillar_id, name, target_weight). */
    listPillars(): PillarView[] {
        const rows = this.db
            .prepare(`SELECT pillar_id, name, target_weight FROM strategy_pillar ORDER BY pillar_id`)
            .all() as Array<{ pillar_id: string; name: string; target_weight: number | null }>;
        return rows.map(r => ({ id: r.pillar_id, name: r.name, targetWeight: r.target_weight }));
    }
}
