/**
 * TradeLogRepository.ts - SQLite persistence for the `trade_log_entry` table.
 *
 * Purpose:
 *   TS-side counterpart to `py_services/domain_model/trade_log_entry_repository.py`
 *   (Domain Data Model v3.2, spec s2.7), reading/writing the same physical
 *   `data/domain_model.sqlite` file via `better-sqlite3`. Mirrors
 *   `PortfolioRepository.ts`'s Wave pattern: a thin repository class wrapping the
 *   Node SQLite driver for this table, with `ensureSchema()` transcribing the same
 *   `CREATE TABLE IF NOT EXISTS` DDL as `db_client.py::initialize_db` (idempotent
 *   no-op against the real file; load-bearing for fresh temp/test databases). No
 *   script or service should open its own connection against `trade_log_entry`
 *   outside this class.
 *
 *   This is the local trade log -- the manually/agent-logged record of planned
 *   and executed trades. Keyed by `entry_id`. Callers resolve `investment_id` via
 *   InvestmentRepository before calling `upsertTradeLogEntry` -- this class is a
 *   pure repository over the DDL's own column names and does not translate JSON
 *   source keys (e.g. `ticker` -> `investment_id`, `totalCost` -> `total_cost`);
 *   that translation is the migration script's job.
 *
 * Layer:
 *   Backend / Services / Data Persistence (SQLite-backed repository)
 *
 * Key Functions (Index):
 *   - upsertTradeLogEntry(entry) - Insert-or-update one `trade_log_entry` row keyed
 *     by `entry_id`, mirrors trade_log_entry_repository.py::upsert_trade_log_entry
 *   - listTradeLogEntries(accountId?) - all rows, optionally filtered by account_id
 *   - getTradeLogEntry(entryId) - single row by entry_id, or null if missing
 *   - deleteTradeLogEntry(entryId) - removes the row
 */
import Database from 'better-sqlite3';

export interface TradeLogEntryRow {
    entry_id: string;
    investment_id: string;
    account_id: string | null;
    action: string | null;
    shares: number | null;
    price: number | null;
    total_cost: number | null;
    order_type: string | null;
    limit_price: number | null;
    trade_date: string | null;
    notes: string | null;
    status: string | null;
    source: string | null;
    priority: string | null;
    logged_at: string | null;
}

const COLUMNS: Array<keyof TradeLogEntryRow> = [
    'entry_id', 'investment_id', 'account_id', 'action', 'shares', 'price',
    'total_cost', 'order_type', 'limit_price', 'trade_date', 'notes',
    'status', 'source', 'priority', 'logged_at',
];

export class TradeLogRepository {
    private db: Database.Database;

    constructor(dbPath: string) {
        this.db = new Database(dbPath);
        this.ensureSchema();
    }

    close(): void {
        this.db.close();
    }

    /** Transcribed from `py_services/domain_model/db_client.py::initialize_db` —
     * see `PortfolioRepository.ts`'s module docstring for the sync contract this
     * mirrors. Idempotent against the real, already-initialized file. Includes the
     * `investment` table since `trade_log_entry.investment_id` is a FK against it,
     * needed for a fresh temp/test database. */
    private ensureSchema(): void {
        this.db.pragma('journal_mode = WAL');
        this.db.pragma('foreign_keys = ON');

        this.db.exec(`
            CREATE TABLE IF NOT EXISTS account (
                account_id      TEXT PRIMARY KEY,
                account_name    TEXT NOT NULL,
                account_type    TEXT,
                base_currency   TEXT NOT NULL DEFAULT 'CAD'
            );

            CREATE TABLE IF NOT EXISTS investment (
                investment_id              TEXT PRIMARY KEY,
                symbol                      TEXT NOT NULL,
                name                        TEXT,
                sector                      TEXT,
                industry                    TEXT,
                pillar_id                   TEXT,
                asset_class                 TEXT NOT NULL,
                currency                    TEXT NOT NULL DEFAULT 'USD',
                updated_at                  TEXT NOT NULL,
                UNIQUE(symbol)
            );

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
        `);
    }

    /** Mirrors `trade_log_entry_repository.py::upsert_trade_log_entry` — insert-
     * or-update one row keyed by `entry_id`. Idempotent: calling twice for the
     * same `entry_id` updates in place rather than inserting a duplicate row. */
    upsertTradeLogEntry(entry: Partial<TradeLogEntryRow> & { entry_id: string }): string {
        const values = COLUMNS.map(col => (entry as any)[col] ?? null);
        const placeholders = COLUMNS.map(() => '?').join(', ');
        const updateClause = COLUMNS.filter(col => col !== 'entry_id')
            .map(col => `${col}=excluded.${col}`)
            .join(', ');

        this.db
            .prepare(
                `INSERT INTO trade_log_entry (${COLUMNS.join(', ')})
                 VALUES (${placeholders})
                 ON CONFLICT(entry_id) DO UPDATE SET ${updateClause}`
            )
            .run(...values);
        return entry.entry_id;
    }

    /** Mirrors `trade_log_entry_repository.py::list_trade_log_entries` — all rows,
     * optionally filtered by `account_id`. */
    listTradeLogEntries(accountId?: string): TradeLogEntryRow[] {
        if (accountId) {
            return this.db
                .prepare('SELECT * FROM trade_log_entry WHERE account_id = ? ORDER BY entry_id')
                .all(accountId) as TradeLogEntryRow[];
        }
        return this.db.prepare('SELECT * FROM trade_log_entry ORDER BY entry_id').all() as TradeLogEntryRow[];
    }

    /** Mirrors `trade_log_entry_repository.py::get_trade_log_entry` — single row
     * by `entry_id`, or null if it does not exist. */
    getTradeLogEntry(entryId: string): TradeLogEntryRow | null {
        const row = this.db
            .prepare('SELECT * FROM trade_log_entry WHERE entry_id = ?')
            .get(entryId) as TradeLogEntryRow | undefined;
        return row ?? null;
    }

    /** Mirrors `trade_log_entry_repository.py::delete_trade_log_entry` — removes
     * the row for `entryId`. No-op if it does not exist. */
    deleteTradeLogEntry(entryId: string): void {
        this.db.prepare('DELETE FROM trade_log_entry WHERE entry_id = ?').run(entryId);
    }
}
