import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { TradeLogRepository } from '../src/services/TradeLogRepository';

describe('TradeLogRepository', () => {
    let repo: TradeLogRepository;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `trade-log-repo-test-${Date.now()}-${Math.random()}.sqlite`);
        repo = new TradeLogRepository(dbPath);
        const db = (repo as any).db;
        db.prepare(
            `INSERT INTO investment (investment_id, symbol, name, asset_class, currency, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)`
        ).run('AAPL', 'AAPL', 'AAPL', 'EQUITY', 'USD', new Date().toISOString());
        db.prepare(
            `INSERT INTO account (account_id, account_name, account_type, base_currency) VALUES (?, ?, ?, ?)`
        ).run('TFSA', 'TFSA', 'TFSA', 'CAD');
        db.prepare(
            `INSERT INTO account (account_id, account_name, account_type, base_currency) VALUES (?, ?, ?, ?)`
        ).run('RRSP', 'RRSP', 'RRSP', 'CAD');
    });

    afterEach(() => {
        repo.close();
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    const fixture = (overrides: Partial<Record<string, any>> = {}) => ({
        entry_id: 'entry-1',
        investment_id: 'AAPL',
        account_id: 'TFSA',
        action: 'BUY',
        shares: 10,
        price: 150.5,
        total_cost: 1505,
        order_type: 'LIMIT',
        limit_price: 150,
        trade_date: '2026-07-20',
        notes: 'test note',
        status: 'FILLED',
        source: 'manual',
        priority: 'HIGH',
        logged_at: '2026-07-20T00:00:00.000Z',
        ...overrides,
    });

    describe('upsertTradeLogEntry', () => {
        it('creates a new row and round-trips via getTradeLogEntry', () => {
            repo.upsertTradeLogEntry(fixture());
            const row = repo.getTradeLogEntry('entry-1');
            expect(row).to.deep.equal(fixture());
        });

        it('is idempotent — a second call for the same entry_id updates in place, no duplicate row', () => {
            repo.upsertTradeLogEntry(fixture());
            repo.upsertTradeLogEntry(fixture({ shares: 20, status: 'CANCELLED' }));

            const rows = repo.listTradeLogEntries();
            expect(rows).to.have.length(1);
            expect(rows[0].shares).to.equal(20);
            expect(rows[0].status).to.equal('CANCELLED');
        });
    });

    describe('listTradeLogEntries', () => {
        it('lists all entries when no accountId filter is given', () => {
            repo.upsertTradeLogEntry(fixture({ entry_id: 'e1', account_id: 'TFSA' }));
            repo.upsertTradeLogEntry(fixture({ entry_id: 'e2', account_id: 'RRSP' }));

            const rows = repo.listTradeLogEntries();
            expect(rows).to.have.length(2);
        });

        it('filters by accountId when provided', () => {
            repo.upsertTradeLogEntry(fixture({ entry_id: 'e1', account_id: 'TFSA' }));
            repo.upsertTradeLogEntry(fixture({ entry_id: 'e2', account_id: 'RRSP' }));

            const rows = repo.listTradeLogEntries('RRSP');
            expect(rows).to.have.length(1);
            expect(rows[0].entry_id).to.equal('e2');
        });
    });

    describe('getTradeLogEntry', () => {
        it('returns null when the entry does not exist', () => {
            expect(repo.getTradeLogEntry('missing')).to.equal(null);
        });
    });

    describe('deleteTradeLogEntry', () => {
        it('removes the row', () => {
            repo.upsertTradeLogEntry(fixture());
            repo.deleteTradeLogEntry('entry-1');
            expect(repo.getTradeLogEntry('entry-1')).to.equal(null);
            expect(repo.listTradeLogEntries()).to.have.length(0);
        });
    });
});
