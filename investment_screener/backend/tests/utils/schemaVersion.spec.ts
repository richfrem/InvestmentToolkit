import { expect } from 'chai';
import Database from 'better-sqlite3';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { ensureSchemaReady, requiredSchemaVersion } from '../../src/utils/schemaVersion';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';

describe('schemaVersion gate (Python owns the schema)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `schema-gate-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('requires the newest migration number present in schema/domain_model', () => {
        expect(requiredSchemaVersion()).to.be.at.least(1);
    });

    it('asks Python to build a brand-new empty database, then proceeds', () => {
        const db = new Database(dbPath);
        ensureSchemaReady(db, dbPath);
        expect(db.pragma('user_version', { simple: true })).to.equal(requiredSchemaVersion());
        const names = (db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all() as { name: string }[]).map(r => r.name);
        expect(names).to.include.members(['account', 'investment', 'sub_strategy', 'schema_migrations']);
        db.close();
    });

    it('is a no-op on an up-to-date database', () => {
        new PortfolioRepository(dbPath).close(); // builds it
        const db = new Database(dbPath);
        expect(() => ensureSchemaReady(db, dbPath)).to.not.throw();
        db.close();
    });

    it('refuses (and does not migrate) a populated database that is behind', () => {
        const db = new Database(dbPath);
        db.exec('CREATE TABLE something (id INTEGER)');
        expect(() => ensureSchemaReady(db, dbPath)).to.throw(/schema version 0[\s\S]*needs[\s\S]*schema_migrator\.py/);
        const still = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all() as { name: string }[];
        expect(still.map(r => r.name)).to.deep.equal(['something']); // untouched
        db.close();
    });

    it('refuses a database newer than this checkout understands', () => {
        const db = new Database(dbPath);
        db.exec('CREATE TABLE something (id INTEGER)');
        db.pragma(`user_version = ${requiredSchemaVersion() + 5}`);
        expect(() => ensureSchemaReady(db, dbPath)).to.throw(/newer than this checkout/);
        db.close();
    });

    it('refuses to build an in-memory database (Python cannot reach it)', () => {
        const db = new Database(':memory:');
        expect(() => ensureSchemaReady(db, ':memory:')).to.throw(/in-memory/);
        db.close();
    });
});
