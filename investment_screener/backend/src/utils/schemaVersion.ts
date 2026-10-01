/**
 * Schema gate for domain_model.sqlite. Node never creates or alters tables.
 *
 * The schema is owned by Python: numbered SQL files in `backend/schema/domain_model/`,
 * applied by `py_services/domain_model/schema_migrator.py`, which records the newest
 * applied version in `PRAGMA user_version`. Every repository calls
 * `ensureSchemaReady()` right after opening its connection.
 *
 *   - version matches the newest migration file   -> proceed
 *   - file is brand new / empty (no user tables)  -> ask the Python migrator to build it
 *     (nothing exists to lose; this is what makes a fresh install or a test database work)
 *   - populated file that is BEHIND               -> refuse, with the command to run.
 *     A real database is migrated deliberately (with a backup), never as a side effect of
 *     a read or a request.
 *   - file is AHEAD of this checkout              -> refuse; the code is older than the data.
 */
import { execFileSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import Database from 'better-sqlite3';

// Same relative depth from src/utils (ts-node) and dist/utils (compiled): ../../ === backend/.
const BACKEND_DIR = path.resolve(__dirname, '..', '..');
export const MIGRATIONS_DIR = path.join(BACKEND_DIR, 'schema', 'domain_model');
const MIGRATOR = path.join(BACKEND_DIR, 'py_services', 'domain_model', 'schema_migrator.py');
const MIGRATION_FILE = /^(\d{4})_[a-z0-9_]+\.sql$/;

/** Newest migration number present in this checkout. */
export function requiredSchemaVersion(): number {
    const versions = fs
        .readdirSync(MIGRATIONS_DIR)
        .map(f => MIGRATION_FILE.exec(f))
        .filter((m): m is RegExpExecArray => m !== null)
        .map(m => parseInt(m[1], 10));
    if (versions.length === 0) {
        throw new Error(`No schema migrations found in ${MIGRATIONS_DIR}`);
    }
    return Math.max(...versions);
}

function userTableCount(db: Database.Database): number {
    const row = db
        .prepare(
            "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        .get() as { n: number };
    return row.n;
}

export function ensureSchemaReady(db: Database.Database, dbPath: string): void {
    const required = requiredSchemaVersion();
    let version = db.pragma('user_version', { simple: true }) as number;
    if (version === required) return;

    const fixCommand = `python3 ${path.relative(process.cwd(), MIGRATOR) || MIGRATOR} --db ${dbPath}`;

    if (version === 0 && userTableCount(db) === 0) {
        if (dbPath === ':memory:' || dbPath === '') {
            throw new Error('An in-memory database cannot be built by the Python migrator; use a file path.');
        }
        try {
            execFileSync(process.env.PYTHON ?? 'python3', [MIGRATOR, '--db', dbPath], {
                stdio: ['ignore', 'pipe', 'pipe'],
            });
        } catch (err) {
            const e = err as { stderr?: Buffer; message: string };
            throw new Error(
                `Could not create the database schema for ${dbPath}: ${e.stderr?.toString().trim() || e.message}`
            );
        }
        version = db.pragma('user_version', { simple: true }) as number;
        if (version === required) return;
    }

    if (version < required) {
        throw new Error(
            `${dbPath} is at schema version ${version} but this backend needs ${required}. ` +
                `Migrate it (a backup is taken first) with: ${fixCommand}`
        );
    }
    throw new Error(
        `${dbPath} is at schema version ${version}, newer than this checkout understands (${required}). ` +
            'Update the code (git pull) before opening this database.'
    );
}
