/**
 * PortfolioRepository.ts - SQLite persistence for the shared `account` and
 * `account_investment` tables.
 *
 * Purpose:
 *   TS-side counterpart to `py_services/domain_model/account_investment_repository.py`
 *   (ADR-029/030), reading/writing the same physical `data/domain_model.sqlite` file
 *   via `better-sqlite3`. Mirrors `InvestmentRepository.ts`'s Wave 2 pattern: a thin
 *   repository class wrapping the Node SQLite driver for these two tables, with
 *   `ensureSchema()` transcribing the same `CREATE TABLE IF NOT EXISTS` DDL as
 *   `db_client.py::initialize_db` (idempotent no-op against the real file;
 *   load-bearing for fresh temp/test databases). No script or service should open
 *   its own connection against `account`/`account_investment` outside this class.
 *
 *   `investment` rows themselves (the FK target of `account_investment.investment_id`)
 *   remain InvestmentRepository.ts's exclusive concern per its own module docstring —
 *   callers here resolve/pass an already-known `investmentId` (e.g. via
 *   `InvestmentRepository.resolveInvestmentId(symbol)`) rather than this class
 *   duplicating that write path.
 *
 * Layer:
 *   Backend / Services / Data Persistence (SQLite-backed repository)
 *
 * Key Functions (Index):
 *   - upsertAccount(accountId, accountName, accountType?, baseCurrency?) - Idempotent
 *     lookup-or-insert/update of an `account` row, mirrors
 *     account_repository.py::upsert_account
 *   - upsertAccountInvestment(accountId, investmentId, quantity, ...) - Insert-or-update
 *     one `account_investment` row keyed by (account_id, investment_id), mirrors
 *     account_investment_repository.py::upsert_account_investment
 *   - listAccountInvestments(accountId?) - Read helper for tests/verification
 */
import Database from 'better-sqlite3';

export interface AccountInvestmentRow {
    account_investment_id: string;
    account_id: string;
    investment_id: string;
    quantity: number;
    average_cost: number | null;
    book_value: number | null;
    currency: string;
    last_synced_at: string;
}

export class PortfolioRepository {
    private db: Database.Database;

    constructor(dbPath: string) {
        this.db = new Database(dbPath);
        this.ensureSchema();
    }

    close(): void {
        this.db.close();
    }

    /** Transcribed from `py_services/domain_model/db_client.py::initialize_db` —
     * see `InvestmentRepository.ts`'s module docstring for the sync contract this
     * mirrors. Idempotent against the real, already-initialized file. */
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
                asset_class                 TEXT NOT NULL,
                currency                    TEXT NOT NULL DEFAULT 'USD',
                updated_at                  TEXT NOT NULL,
                UNIQUE(symbol)
            );

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

            CREATE INDEX IF NOT EXISTS idx_account_investment_account ON account_investment(account_id);
            CREATE INDEX IF NOT EXISTS idx_account_investment_investment ON account_investment(investment_id);
        `);
    }

    /** Mirrors `account_repository.py::upsert_account` — idempotent
     * lookup-or-insert/update of the `account` row for `accountId`. */
    upsertAccount(accountId: string, accountName: string, accountType: string | null = null, baseCurrency = 'CAD'): void {
        this.db
            .prepare(
                `INSERT INTO account (account_id, account_name, account_type, base_currency)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT(account_id) DO UPDATE SET
                 account_name = excluded.account_name,
                 account_type = excluded.account_type,
                 base_currency = excluded.base_currency`
            )
            .run(accountId, accountName, accountType, baseCurrency);
    }

    /** Mirrors `account_investment_repository.py::upsert_account_investment` —
     * insert-or-update one row keyed by (account_id, investment_id). Calling
     * twice for the same (account, investment) pair updates in place rather
     * than inserting a duplicate row. Assumes `investmentId` already resolved
     * (e.g. via `InvestmentRepository.resolveInvestmentId(symbol)`) — this
     * class never writes the `investment` table itself. */
    upsertAccountInvestment(
        accountId: string,
        investmentId: string,
        quantity: number,
        averageCost: number | null,
        bookValue: number | null,
        currency: string,
        lastSyncedAt: string
    ): string {
        const accountInvestmentId = `${accountId}:${investmentId}`;
        this.db
            .prepare(
                `INSERT INTO account_investment
                 (account_investment_id, account_id, investment_id, quantity, average_cost, book_value, currency, last_synced_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT(account_id, investment_id) DO UPDATE SET
                 quantity = excluded.quantity,
                 average_cost = excluded.average_cost,
                 book_value = excluded.book_value,
                 currency = excluded.currency,
                 last_synced_at = excluded.last_synced_at`
            )
            .run(accountInvestmentId, accountId, investmentId, quantity, averageCost, bookValue, currency, lastSyncedAt);
        return accountInvestmentId;
    }

    /** Read helper: all `account_investment` rows, optionally filtered by account. */
    listAccountInvestments(accountId?: string): AccountInvestmentRow[] {
        if (accountId) {
            return this.db
                .prepare('SELECT * FROM account_investment WHERE account_id = ? ORDER BY investment_id')
                .all(accountId) as AccountInvestmentRow[];
        }
        return this.db.prepare('SELECT * FROM account_investment ORDER BY account_id, investment_id').all() as AccountInvestmentRow[];
    }
}
