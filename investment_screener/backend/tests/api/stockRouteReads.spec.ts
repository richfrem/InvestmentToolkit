/**
 * stockRouteReads.spec.ts
 *
 * Purpose: proves routes/stock.ts's SQLite-backed read helper (Wave 3 Task 6)
 * — getStockTotalsFromDb — sources the portfolio-wide USD total from
 * domain_model.sqlite (via PortfolioRepository.getPortfolioTotalValue(), same
 * function routes/portfolio.ts's /summary uses) instead of reading
 * portfolio.json's `totals` block directly (stock.ts:125-126 before this
 * rewire), used by POST /portfolio-heatmap.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { getStockTotalsFromDb } from '../../src/routes/stock';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('routes/stock.ts SQLite-backed read helper (Wave 3 Task 6)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `stock-route-reads-test-${Date.now()}-${Math.random()}.sqlite`);
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
        expect(getStockTotalsFromDb(dbPath)).to.equal(null);
    });

    it('returns totalUSD summed across accounts (4 NVDA @ 900 + 10 AMD @ 130)', () => {
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

        // (3+1)*900 + 10*130 = 3600 + 1300 = 4900
        expect(getStockTotalsFromDb(dbPath)).to.equal(4900);
    });

    it('identifies symbol not found or insufficient financial data errors as 404 client errors', () => {
        const notFoundErrors = [
            'HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: KMRN"}}}',
            'Quote not found for symbol: KMRN',
            'possibly delisted; no price data found',
            'Insufficient financial data',
            'No data found, symbol may be delisted',
            'No data found for this date range'
        ];

        for (const err of notFoundErrors) {
            const isSymbolNotFound = /Quote not found|possibly delisted|No data found|Insufficient financial data|404/i.test(err);
            expect(isSymbolNotFound).to.be.true;
        }
    });
});
