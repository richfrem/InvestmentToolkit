/**
 * tradingTradeLogSqlite.spec.ts
 *
 * Purpose: proves routes/trading.ts's readLog()/writeLog() (Wave 4 Task 11
 * cutover) are backed by the trade_log_entry SQLite table via
 * TradeLogRepository, not trade-log.json (retired/archived) — while
 * preserving the exact external JSON entry shape every route handler
 * (GET /log, POST /log, PATCH /log/:id, /modify, /cancel,
 * /log/sync-from-tv) already relies on.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { readLog, writeLog } from '../../src/routes/trading';

describe('routes/trading.ts readLog()/writeLog() (Wave 4 Task 11 SQLite cutover)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `trading-tradelog-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    const entry = (overrides: Partial<Record<string, any>> = {}) => ({
        id: 'e1',
        ticker: 'NVDA',
        action: 'buy',
        shares: 10,
        price: 200,
        totalCost: 2000,
        account: 'TFSA',
        orderType: 'market',
        limitPrice: null,
        date: '2026-07-20',
        notes: 'test',
        status: 'logged',
        source: 'manual',
        priority: null,
        tvOrderId: null,
        loggedAt: '2026-07-20T00:00:00.000Z',
        ...overrides,
    });

    it('readLog() returns [] against a fresh/empty DB', () => {
        expect(readLog(dbPath)).to.deep.equal([]);
    });

    it('writeLog() then readLog() round-trips an entry with the original JSON shape', () => {
        writeLog([entry()], dbPath);
        const entries = readLog(dbPath);
        expect(entries).to.have.length(1);
        expect(entries[0]).to.deep.equal(entry());
    });

    it('writeLog() upserts in place — a second call with the same id updates, no duplicate row', () => {
        writeLog([entry()], dbPath);
        writeLog([entry({ status: 'cancelled', shares: 20 })], dbPath);

        const entries = readLog(dbPath);
        expect(entries).to.have.length(1);
        expect(entries[0].status).to.equal('cancelled');
        expect(entries[0].shares).to.equal(20);
    });

    it('preserves tvOrderId across writeLog/readLog (needed by /modify, /cancel, /log/sync-from-tv)', () => {
        writeLog([entry({ tvOrderId: 'tv-order-123', status: 'submitted' })], dbPath);
        const entries = readLog(dbPath);
        expect(entries[0].tvOrderId).to.equal('tv-order-123');
    });

    it('readLog() returns entries newest-first by loggedAt, matching the old unshift() order', () => {
        writeLog([
            entry({ id: 'e1', loggedAt: '2026-07-20T00:00:00.000Z' }),
            entry({ id: 'e2', loggedAt: '2026-07-21T00:00:00.000Z' }),
            entry({ id: 'e3', loggedAt: '2026-07-19T00:00:00.000Z' }),
        ], dbPath);

        const ids = readLog(dbPath).map(e => e.id);
        expect(ids).to.deep.equal(['e2', 'e1', 'e3']);
    });

    it('writeLog() resolves ticker -> investment_id and creates the account row if new', () => {
        writeLog([entry({ ticker: 'aapl', account: 'RRSP' })], dbPath);
        const entries = readLog(dbPath);
        expect(entries[0].ticker).to.equal('AAPL');
        expect(entries[0].account).to.equal('RRSP');
    });
});
