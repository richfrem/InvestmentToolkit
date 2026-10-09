/**
 * ThesisBreakerRepository.ts - SQLite persistence for `thesis_breaker` and `thesis_breaker_state`.
 *
 * Purpose:
 *   TS-side counterpart to `py_services/domain_model/thesis_breaker_repository.py`. Same
 *   definition and state shapes, same validation, same vocabulary. Definitions are
 *   human-owned (edited through the thesis tools); state is written by the evaluator and
 *   `investment.thesis_breaker_status` is derived from it (worst current status).
 *
 * Layer:
 *   Backend / Services / Data Persistence (SQLite-backed repository)
 *
 * Key Functions:
 *   - validateBreaker(breaker) - error strings for a definition
 *   - listBreakers(symbol) / listAllBreakers() - definitions for one ticker / every ticker
 *   - upsertBreaker(), deleteBreaker(), setManualStatus()
 *   - replaceBreakerState(state) / listBreakerState()
 *
 * Key Input Dependencies:
 *   - domain_model.sqlite at schema version 2 or later (checked by ensureSchemaReady)
 */
import Database from 'better-sqlite3';
import { ensureSchemaReady } from '../utils/schemaVersion';

export const AUTO_METRICS = ['rsi', 'dcfFairValueGapPct', 'trendState', 'momentumPercentile', 'pillarAvgScore'] as const;
export const VALID_OPERATORS = ['<', '<=', '>', '>=', '==', 'in'] as const;
export const VALID_STATUSES = ['OK', 'WATCHING', 'TRIGGERED'] as const;
type Status = (typeof VALID_STATUSES)[number];
const SEVERITY: Record<string, number> = { OK: 0, WATCHING: 1, TRIGGERED: 2 };

export interface BreakerDefinition {
    id: string;
    type: 'auto' | 'manual';
    metric?: string;
    operator: string;
    threshold?: unknown;
    horizon?: unknown;
    note?: string;
    status?: string;
    statusSetAt?: string;
    reviewCadenceDays?: number;
}

export type BreakerStateEntry = Record<string, unknown> & { type: 'auto' | 'manual'; status: Status };
export type BreakerState = Record<string, Record<string, BreakerStateEntry>>;

interface DefinitionRow {
    breaker_id: string; breaker_type: 'auto' | 'manual'; metric: string | null; operator: string;
    threshold_json: string | null; horizon_json: string | null; note: string | null; status: string | null;
    status_set_at: string | null; review_cadence_days: number | null; symbol: string;
}

const parse = (text: string | null): unknown => (text === null ? null : JSON.parse(text));
const dump = (value: unknown): string | null => (value === undefined || value === null ? null : JSON.stringify(value));

export function validateBreaker(b: Partial<BreakerDefinition>): string[] {
    const errors: string[] = [];
    if (!b.id) errors.push("breaker missing 'id'");
    if (b.type !== 'auto' && b.type !== 'manual') errors.push(`breaker 'type' must be 'auto' or 'manual', got ${JSON.stringify(b.type)}`);
    if (b.type === 'auto' && !(AUTO_METRICS as readonly string[]).includes(b.metric ?? '')) {
        errors.push(`auto breaker 'metric' must be one of ${AUTO_METRICS.join(', ')}, got ${JSON.stringify(b.metric)}`);
    }
    if (!(VALID_OPERATORS as readonly string[]).includes(b.operator ?? '')) {
        errors.push(`'operator' must be one of ${VALID_OPERATORS.join(', ')}, got ${JSON.stringify(b.operator)}`);
    }
    if (b.operator === 'in' && !Array.isArray(b.threshold)) errors.push("operator 'in' requires 'threshold' to be a list");
    if (b.type === 'manual') {
        if (!(VALID_STATUSES as readonly string[]).includes(b.status ?? '')) {
            errors.push(`manual breaker 'status' must be one of ${VALID_STATUSES.join(', ')}, got ${JSON.stringify(b.status)}`);
        }
        if (!b.statusSetAt) errors.push("manual breaker missing 'statusSetAt'");
        if (!b.reviewCadenceDays) errors.push("manual breaker missing 'reviewCadenceDays'");
    }
    return errors;
}

function toDefinition(r: DefinitionRow): BreakerDefinition {
    const out: BreakerDefinition = { id: r.breaker_id, type: r.breaker_type } as BreakerDefinition;
    if (r.metric !== null) out.metric = r.metric;
    out.operator = r.operator;
    out.threshold = parse(r.threshold_json);
    if (r.horizon_json !== null) out.horizon = parse(r.horizon_json);
    if (r.note !== null) out.note = r.note;
    if (r.breaker_type === 'manual') {
        out.status = r.status ?? undefined;
        out.statusSetAt = r.status_set_at ?? undefined;
        out.reviewCadenceDays = r.review_cadence_days ?? undefined;
    }
    return out;
}

export class ThesisBreakerRepository {
    private db: Database.Database;

    constructor(dbPath: string) {
        this.db = new Database(dbPath);
        this.db.pragma('journal_mode = WAL');
        this.db.pragma('foreign_keys = ON');
        ensureSchemaReady(this.db, dbPath);
    }

    close(): void {
        this.db.close();
    }

    private investmentId(symbol: string): string {
        const row = this.db.prepare('SELECT investment_id FROM investment WHERE symbol = ?').get(symbol) as
            { investment_id: string } | undefined;
        if (!row) throw new Error(`ticker '${symbol}' not found in domain_model.sqlite`);
        return row.investment_id;
    }

    private selectDefinitions(where: string, ...params: string[]): DefinitionRow[] {
        return this.db.prepare(
            `SELECT b.*, i.symbol AS symbol FROM thesis_breaker b
             JOIN investment i ON i.investment_id = b.investment_id ${where} ORDER BY i.symbol, b.rowid`
        ).all(...params) as DefinitionRow[];
    }

    listBreakers(symbol: string): BreakerDefinition[] {
        return this.selectDefinitions('WHERE i.symbol = ?', symbol).map(toDefinition);
    }

    listAllBreakers(): Record<string, BreakerDefinition[]> {
        const out: Record<string, BreakerDefinition[]> = {};
        for (const r of this.selectDefinitions('')) (out[r.symbol] ??= []).push(toDefinition(r));
        return out;
    }

    upsertBreaker(symbol: string, b: BreakerDefinition): void {
        const errors = validateBreaker(b);
        if (errors.length) throw new Error(`Invalid breaker: ${errors.join('; ')}`);
        const investmentId = this.investmentId(symbol);
        const manual = b.type === 'manual';
        this.db.prepare(
            `INSERT INTO thesis_breaker (breaker_id, investment_id, breaker_type, metric, operator, threshold_json,
                 horizon_json, note, status, status_set_at, review_cadence_days, created_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
             ON CONFLICT (investment_id, breaker_id) DO UPDATE SET
                 breaker_type = excluded.breaker_type, metric = excluded.metric, operator = excluded.operator,
                 threshold_json = excluded.threshold_json, horizon_json = excluded.horizon_json, note = excluded.note,
                 status = excluded.status, status_set_at = excluded.status_set_at,
                 review_cadence_days = excluded.review_cadence_days`
        ).run(b.id, investmentId, b.type, b.metric ?? null, b.operator, dump(b.threshold), dump(b.horizon),
            b.note ?? null, manual ? b.status : null, manual ? b.statusSetAt : null,
            manual ? b.reviewCadenceDays : null, new Date().toISOString());
    }

    deleteBreaker(symbol: string, breakerId: string): void {
        const investmentId = this.investmentId(symbol);
        const exists = this.db.prepare('SELECT 1 FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?')
            .get(investmentId, breakerId);
        if (!exists) throw new Error(`breaker id '${breakerId}' not found on ${symbol}`);
        this.db.transaction(() => {
            this.db.prepare('DELETE FROM thesis_breaker_state WHERE investment_id = ? AND breaker_id = ?').run(investmentId, breakerId);
            this.db.prepare('DELETE FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?').run(investmentId, breakerId);
            this.refreshInvestmentStatus();
        })();
    }

    setManualStatus(symbol: string, breakerId: string, status: string, note: string | null, today?: string): void {
        if (!(VALID_STATUSES as readonly string[]).includes(status)) {
            throw new Error(`status must be one of ${VALID_STATUSES.join(', ')}, got ${JSON.stringify(status)}`);
        }
        const investmentId = this.investmentId(symbol);
        const row = this.db.prepare('SELECT breaker_type, note FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?')
            .get(investmentId, breakerId) as { breaker_type: string; note: string | null } | undefined;
        if (!row) throw new Error(`breaker id '${breakerId}' not found on ${symbol}`);
        if (row.breaker_type !== 'manual') {
            throw new Error(`breaker '${breakerId}' is type '${row.breaker_type}' — status can only be set on manual breakers`);
        }
        const date = today ?? new Date().toISOString().slice(0, 10);
        const newNote = note ? (row.note ? `${row.note} | status update ${date}: ${note}` : note) : row.note;
        this.db.prepare('UPDATE thesis_breaker SET status = ?, status_set_at = ?, note = ? WHERE investment_id = ? AND breaker_id = ?')
            .run(status, date, newNote, investmentId, breakerId);
    }

    replaceBreakerState(state: BreakerState): void {
        const rows: unknown[][] = [];
        for (const [symbol, breakers] of Object.entries(state)) {
            const investmentId = this.investmentId(symbol);
            for (const [breakerId, e] of Object.entries(breakers)) {
                const known = this.db.prepare('SELECT 1 FROM thesis_breaker WHERE investment_id = ? AND breaker_id = ?')
                    .get(investmentId, breakerId);
                if (!known) throw new Error(`breaker id '${breakerId}' not found on ${symbol}`);
                rows.push([investmentId, breakerId, e.status, dump(e.currentValue),
                    e.conditionMet === undefined || e.conditionMet === null ? null : Number(e.conditionMet),
                    e.currentStreak ?? null, e.streakStartDate ?? null,
                    e.lastEvaluatedAt ?? new Date().toISOString(), e.daysSinceReview ?? null,
                    e.stale === undefined || e.stale === null ? null : Number(e.stale)]);
            }
        }
        const insert = this.db.prepare(
            `INSERT INTO thesis_breaker_state (investment_id, breaker_id, status, current_value_json, condition_met,
                 current_streak, streak_start_date, last_evaluated_at, days_since_review, is_stale)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
        );
        this.db.transaction(() => {
            this.db.prepare('DELETE FROM thesis_breaker_state').run();
            for (const r of rows) insert.run(...r);
            this.refreshInvestmentStatus();
        })();
    }

    private refreshInvestmentStatus(): void {
        this.db.prepare('UPDATE investment SET thesis_breaker_status = NULL WHERE thesis_breaker_status IS NOT NULL').run();
        const worst = new Map<string, string>();
        const states = this.db.prepare('SELECT investment_id, status FROM thesis_breaker_state')
            .all() as Array<{ investment_id: string; status: string }>;
        for (const s of states) {
            if (SEVERITY[s.status] >= SEVERITY[worst.get(s.investment_id) ?? 'OK']) worst.set(s.investment_id, s.status);
        }
        const update = this.db.prepare('UPDATE investment SET thesis_breaker_status = ? WHERE investment_id = ?');
        for (const [id, status] of worst) update.run(status, id);
    }

    listBreakerState(): BreakerState {
        const rows = this.db.prepare(
            `SELECT s.*, i.symbol AS symbol, b.breaker_type AS breaker_type, b.status_set_at AS status_set_at,
                    b.review_cadence_days AS review_cadence_days
             FROM thesis_breaker_state s
             JOIN investment i ON i.investment_id = s.investment_id
             JOIN thesis_breaker b ON b.investment_id = s.investment_id AND b.breaker_id = s.breaker_id
             ORDER BY i.symbol, b.rowid`
        ).all() as Array<Record<string, any>>;
        const out: BreakerState = {};
        for (const r of rows) {
            const entry: BreakerStateEntry = r.breaker_type === 'auto'
                ? { type: 'auto', currentValue: parse(r.current_value_json),
                    conditionMet: r.condition_met === null ? null : Boolean(r.condition_met),
                    currentStreak: r.current_streak, streakStartDate: r.streak_start_date,
                    lastEvaluatedAt: r.last_evaluated_at, status: r.status }
                : { type: 'manual', status: r.status, statusSetAt: r.status_set_at,
                    reviewCadenceDays: r.review_cadence_days, daysSinceReview: r.days_since_review,
                    stale: r.is_stale === null ? null : Boolean(r.is_stale) };
            (out[r.symbol] ??= {})[r.breaker_id] = entry;
        }
        return out;
    }
}
