/**
 * portfolioSummaryPriceAge.spec.ts
 *
 * The Portfolio Summary's "as of" time is the oldest price behind the portfolio value, not the
 * position-sync time: a sync can succeed while the price refresh fails, and the page must not
 * look current when the prices are not. Cash prices are ignored (every sync rewrites them).
 *
 * All state is tmp_path-scoped SQLite via the real repositories, never the real database.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { getOldestPositionPriceAtFromDb } from '../../src/routes/portfolio';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('routes/portfolio.ts summary "as of" time', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `portfolio-price-age-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    function seed(prices: Record<string, string>, cashFetchedAt: string) {
        const investmentRepo = new InvestmentRepository(dbPath);
        const portfolioRepo = new PortfolioRepository(dbPath);
        portfolioRepo.upsertAccount('TFSA', 'TFSA', 'TFSA');
        for (const [symbol, fetchedAt] of Object.entries(prices)) {
            const id = investmentRepo.resolveInvestmentId(symbol, 'EQUITY', 'USD');
            portfolioRepo.upsertAccountInvestment('TFSA', id, 1, 100, 100, 'USD', fetchedAt);
            portfolioRepo.upsertInvestmentPrice(id, 100, 'USD', fetchedAt);
        }
        const cashId = investmentRepo.resolveInvestmentId('CASH_USD', 'CASH', 'USD');
        portfolioRepo.upsertAccountInvestment('TFSA', cashId, 5, 1, 5, 'USD', cashFetchedAt);
        portfolioRepo.upsertInvestmentPrice(cashId, 1, 'USD', cashFetchedAt);
        investmentRepo.close();
        portfolioRepo.close();
    }

    it('returns null when there is no priced position', () => {
        expect(getOldestPositionPriceAtFromDb(dbPath)).to.equal(null);
    });

    it('is the oldest held price, so one stale stock keeps the whole total looking stale', () => {
        seed({ NVDA: '2026-10-28T03:11:00.000Z', AAPL: '2026-10-20T15:00:00.000Z' }, '2026-10-28T05:00:00.000Z');
        expect(getOldestPositionPriceAtFromDb(dbPath)).to.equal('2026-10-20T15:00:00.000Z');
    });

    it('ignores the cash price, which every position sync rewrites', () => {
        seed({ NVDA: '2026-10-28T03:11:00.000Z' }, '2026-10-28T09:00:00.000Z');
        expect(getOldestPositionPriceAtFromDb(dbPath)).to.equal('2026-10-28T03:11:00.000Z');
    });
});
