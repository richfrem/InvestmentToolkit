/**
 * PortfolioChangeLogRepository.ts - SQLite persistence for `portfolio_change_log`.
 *
 * Purpose:
 *   TS-side counterpart to
 *   `py_services/domain_model/portfolio_change_log_repository.py` (Wave 8).
 *   Portfolio-wide version history (target-portfolio.json's former top-level
 *   `changeLog` array: {version, date, note} per entry) -- append-only, never
 *   overwrite/replace an existing entry.
 */
import Database from 'better-sqlite3';

export interface ChangeLogEntry {
    entryId: string;
    version: string;
    entryDate: string;
    note: string;
    createdAt: string;
}

export class PortfolioChangeLogRepository {
    private db: Database.Database;

    constructor(dbPath: string) {
        this.db = new Database(dbPath);
        this.ensureSchema();
    }

    close(): void {
        this.db.close();
    }

    private ensureSchema(): void {
        this.db.pragma('journal_mode = WAL');
        this.db.exec(`
            CREATE TABLE IF NOT EXISTS portfolio_change_log (
                entry_id        TEXT PRIMARY KEY,
                version         TEXT NOT NULL,
                entry_date      TEXT NOT NULL,
                note            TEXT NOT NULL,
                created_at      TEXT NOT NULL
            );
        `);
    }

    addEntry(version: string, entryDate: string, note: string, createdAt: string): string {
        const entryId = `changelog-${Math.random().toString(16).slice(2, 10)}`;
        this.db
            .prepare(
                `INSERT INTO portfolio_change_log (entry_id, version, entry_date, note, created_at)
                 VALUES (?, ?, ?, ?, ?)`
            )
            .run(entryId, version, entryDate, note, createdAt);
        return entryId;
    }

    listEntries(): ChangeLogEntry[] {
        const rows = this.db
            .prepare('SELECT * FROM portfolio_change_log ORDER BY entry_date ASC, created_at ASC')
            .all() as Array<{ entry_id: string; version: string; entry_date: string; note: string; created_at: string }>;
        return rows.map(r => ({ entryId: r.entry_id, version: r.version, entryDate: r.entry_date, note: r.note, createdAt: r.created_at }));
    }
}
