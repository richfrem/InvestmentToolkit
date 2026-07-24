/**
 * portfolioRouteReads.spec.ts
 *
 * Purpose: proves routes/portfolio.ts's SQLite-backed read helpers (Wave 3 Task 6)
 * — getPortfolioTotalUsdFromDb, getWeightsFromDb, getStrategyAllocationInputFromDb,
 * getAccountPositionsFromDb — read real numbers from account_investment/
 * investment_price via a tmp-scoped SQLite file, never the real domain_model.sqlite.
 *
 * These are the functions /summary, /weights, /strategy-allocation,
 * /position/:ticker, and /holdings/:ticker are wired to call in place of
 * portfolio.json's `totals`/`tvSnapshot.positions[]` reads.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import {
    getPortfolioTotalUsdFromDb,
    getWeightsFromDb,
    getStrategyAllocationInputFromDb,
    getAccountPositionsFromDb,
    getLastSyncedAtFromDb,
} from '../../src/routes/portfolio';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('routes/portfolio.ts SQLite-backed read helpers (Wave 3 Task 6)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `portfolio-route-reads-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    function seed() {
        const investmentRepo = new InvestmentRepository(dbPath);
        const portfolioRepo = new PortfolioRepository(dbPath);
        const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
        const amdId = investmentRepo.resolveInvestmentId('AMD', 'EQUITY', 'USD');
        const now = new Date().toISOString();
        portfolioRepo.upsertAccount('TFSA', 'TFSA', 'TFSA');
        portfolioRepo.upsertAccount('RRSP', 'RRSP', 'RRSP');
        portfolioRepo.upsertAccountInvestment('TFSA', nvdaId, 3, 800, 2400, 'USD', now);
        portfolioRepo.upsertAccountInvestment('RRSP', nvdaId, 1, 800, 800, 'USD', now);
        portfolioRepo.upsertAccountInvestment('TFSA', amdId, 10, 120, 1200, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(nvdaId, 900, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(amdId, 130, 'USD', now);
        investmentRepo.close();
        portfolioRepo.close();
    }

    it('getPortfolioTotalUsdFromDb returns null on an empty db', () => {
        // Touch the file so ensureSchema runs, but write nothing.
        const repo = new PortfolioRepository(dbPath);
        repo.close();
        expect(getPortfolioTotalUsdFromDb(dbPath)).to.equal(null);
    });

    it('getPortfolioTotalUsdFromDb sums per-account totals (4 NVDA @ 900 + 10 AMD @ 130)', () => {
        seed();
        // (3+1)*900 + 10*130 = 3600 + 1300 = 4900
        expect(getPortfolioTotalUsdFromDb(dbPath)).to.equal(4900);
    });

    it('getWeightsFromDb returns per-symbol percentage weights summing to ~100', () => {
        seed();
        const weights = getWeightsFromDb(dbPath)!;
        expect(weights).to.not.equal(null);
        expect(weights.NVDA).to.be.closeTo((3600 / 4900) * 100, 0.01);
        expect(weights.AMD).to.be.closeTo((1300 / 4900) * 100, 0.01);
    });

    it('getStrategyAllocationInputFromDb returns positions + totalUSD sourced from SQLite', () => {
        seed();
        const input = getStrategyAllocationInputFromDb(dbPath)!;
        expect(input).to.not.equal(null);
        expect(input.totals.totalUSD).to.equal(4900);
        const nvda = input.positions.find(p => p.symbol === 'NVDA');
        expect(nvda.shares).to.equal(4);
        expect(nvda.price).to.equal(900);
    });

    it('getAccountPositionsFromDb returns per-account quantity/average_cost for a ticker', () => {
        seed();
        const rows = getAccountPositionsFromDb('NVDA', dbPath);
        expect(rows).to.have.length(2);
        const tfsa = rows.find(r => r.accountId === 'TFSA')!;
        expect(tfsa.quantity).to.equal(3);
        expect(tfsa.averageCost).to.equal(800);
    });

    it('getAccountPositionsFromDb returns [] for a symbol with no rows', () => {
        seed();
        expect(getAccountPositionsFromDb('MSFT', dbPath)).to.deep.equal([]);
    });

    it('getLastSyncedAtFromDb returns null on an empty db', () => {
        const repo = new PortfolioRepository(dbPath);
        repo.close();
        expect(getLastSyncedAtFromDb(dbPath)).to.equal(null);
    });

    it('getLastSyncedAtFromDb returns the real, current sync timestamp (not frozen)', () => {
        seed();
        const before = getLastSyncedAtFromDb(dbPath);
        expect(before).to.not.equal(null);

        // Simulate a later refresh: a fresh sync writes a new last_synced_at.
        const investmentRepo = new InvestmentRepository(dbPath);
        const portfolioRepo = new PortfolioRepository(dbPath);
        const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
        const later = new Date(Date.now() + 60_000).toISOString();
        portfolioRepo.upsertAccountInvestment('TFSA', nvdaId, 3, 800, 2400, 'USD', later);
        investmentRepo.close();
        portfolioRepo.close();

        expect(getLastSyncedAtFromDb(dbPath)).to.equal(later);
        expect(getLastSyncedAtFromDb(dbPath)).to.not.equal(before);
    });
});
