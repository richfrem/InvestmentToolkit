import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { PortfolioRepository } from '../src/services/PortfolioRepository';

describe('PortfolioRepository', () => {
    let repo: PortfolioRepository;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `portfolio-repo-test-${Date.now()}-${Math.random()}.sqlite`);
        repo = new PortfolioRepository(dbPath);
        // Fixture investment row (owned by InvestmentRepository in production,
        // inserted directly here since this repo never writes `investment` itself).
        const db = (repo as any).db;
        db.prepare(
            `INSERT INTO investment (investment_id, symbol, name, asset_class, currency, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)`
        ).run('AAPL', 'AAPL', 'AAPL', 'EQUITY', 'USD', new Date().toISOString());
    });

    afterEach(() => {
        repo.close();
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    describe('upsertAccountInvestment', () => {
        it('round-trips a write+read for a fixture account/investment/quantity', () => {
            repo.upsertAccount('TFSA', 'TFSA', 'TFSA', 'CAD');
            repo.upsertAccountInvestment('TFSA', 'AAPL', 10, 150.5, 1505, 'USD', '2026-07-20T00:00:00.000Z');

            const rows = repo.listAccountInvestments('TFSA');
            expect(rows).to.have.length(1);
            expect(rows[0]).to.deep.equal({
                account_investment_id: 'TFSA:AAPL',
                account_id: 'TFSA',
                investment_id: 'AAPL',
                quantity: 10,
                average_cost: 150.5,
                book_value: 1505,
                currency: 'USD',
                last_synced_at: '2026-07-20T00:00:00.000Z',
            });
        });

        it('is idempotent — a second call for the same (account, investment) updates in place, no duplicate row', () => {
            repo.upsertAccount('TFSA', 'TFSA');
            repo.upsertAccountInvestment('TFSA', 'AAPL', 10, 150.5, 1505, 'USD', '2026-07-20T00:00:00.000Z');
            repo.upsertAccountInvestment('TFSA', 'AAPL', 12, 151.0, 1812, 'USD', '2026-07-21T00:00:00.000Z');

            const rows = repo.listAccountInvestments('TFSA');
            expect(rows).to.have.length(1);
            expect(rows[0].quantity).to.equal(12);
            expect(rows[0].last_synced_at).to.equal('2026-07-21T00:00:00.000Z');
        });
    });

    describe('exchange rate (broker_exchange_rate singleton)', () => {
        it('returns null when never synced', () => {
            expect(repo.getExchangeRate()).to.equal(null);
        });

        it('round-trips a rate and overwrites the single row idempotently', () => {
            repo.upsertExchangeRate(1.3795, '2026-07-20T00:00:00.000Z');
            expect(repo.getExchangeRate()).to.equal(1.3795);
            repo.upsertExchangeRate(1.4012, '2026-07-21T00:00:00.000Z');
            expect(repo.getExchangeRate()).to.equal(1.4012);
            const db = (repo as any).db;
            const count = db.prepare('SELECT COUNT(*) AS c FROM broker_exchange_rate').get().c;
            expect(count).to.equal(1);
        });
    });
});
