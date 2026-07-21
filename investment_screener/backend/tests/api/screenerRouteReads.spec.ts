/**
 * screenerRouteReads.spec.ts
 *
 * Purpose: proves routes/screener.ts's SQLite-backed read helper (Wave 3 Task 6)
 * — getScreenerPositionsFromDb — reads per-symbol quantity/price aggregated from
 * account_investment/investment_price via a tmp-scoped SQLite file, never the
 * real domain_model.sqlite, replacing GET /all-holdings' portfolio.json
 * `holdings`/flat-array read (screener.ts:95-96 before this rewire).
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { getScreenerPositionsFromDb } from '../../src/routes/screener';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('routes/screener.ts SQLite-backed read helper (Wave 3 Task 6)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `screener-route-reads-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('returns null when the tmp SQLite db has no priced positions', () => {
        const repo = new PortfolioRepository(dbPath);
        repo.close();
        expect(getScreenerPositionsFromDb(dbPath)).to.equal(null);
    });

    it('returns {symbol, shares, price} per ticker aggregated across accounts', () => {
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

        const positions = getScreenerPositionsFromDb(dbPath)!;
        expect(positions).to.not.equal(null);
        const nvda = positions.find(p => p.symbol === 'NVDA')!;
        expect(nvda.shares).to.equal(4);
        expect(nvda.price).to.equal(900);
        const amd = positions.find(p => p.symbol === 'AMD')!;
        expect(amd.shares).to.equal(10);
        expect(amd.price).to.equal(130);
    });
});
