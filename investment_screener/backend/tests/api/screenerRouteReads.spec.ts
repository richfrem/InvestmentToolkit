/**
 * screenerRouteReads.spec.ts
 *
 * Purpose: proves routes/screener.ts's SQLite-backed read helper
 * — getScreenerPositionsFromDb — reads per-symbol quantity/price aggregated from
 * account_investment/investment_price via a tmp-scoped SQLite file, never the
 * real domain_model.sqlite, for GET /all-holdings.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { getScreenerPositionsFromDb, buildActualPctMap, getProjectedTickersFromDb } from '../../src/routes/screener';
import { getWeightsFromDb } from '../../src/routes/portfolio';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';
import { ProjectionRepository } from '../../src/services/ProjectionRepository';
import { ProjectionSchema, Projection } from '../../src/utils/zod-schemas';

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

// Regression coverage for the 2026-07-27 bug: /all-holdings reimplemented its
// own shares*price/totalValue pct math instead of reusing getWeightsFromDb()
// (the same function /api/portfolio/weights serves). Each was individually
// self-consistent (summed to 100% alone), but the two could disagree
// ticker-for-ticker (symbol-normalization drift), so the frontend's per-row
// value depended on which source it happened to read — surfacing as the
// UI's total not summing to 100% even though both backend endpoints did.
describe('buildActualPctMap — single source of truth for current weight %', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `screener-actual-pct-map-test-${Date.now()}-${Math.random()}.sqlite`);
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
        portfolioRepo.upsertAccountInvestment('TFSA', nvdaId, 3, 800, 2400, 'USD', now);
        portfolioRepo.upsertAccountInvestment('TFSA', amdId, 10, 120, 1200, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(nvdaId, 900, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(amdId, 130, 'USD', now);
        investmentRepo.close();
        portfolioRepo.close();
    }

    it('uses getWeightsFromDb() values exactly — no independent recomputation drift', () => {
        seed();
        const positions = getScreenerPositionsFromDb(dbPath)!;
        const dbWeights = getWeightsFromDb(dbPath);
        const actualMap = buildActualPctMap(positions, dbWeights);

        for (const ticker of Object.keys(dbWeights!)) {
            expect(actualMap[ticker].pct).to.equal(dbWeights![ticker]);
        }
        const total = Object.values(actualMap).reduce((s, v) => s + v.pct, 0);
        expect(total).to.be.closeTo(100, 0.001);
    });

    it('falls back to shares*price/totalValue math when dbWeights is null (no priced positions yet)', () => {
        const positions = [
            { symbol: 'NVDA', shares: 3, price: 900 },
            { symbol: 'AMD', shares: 10, price: 130 },
        ];
        const actualMap = buildActualPctMap(positions, null);
        const total = Object.values(actualMap).reduce((s, v) => s + v.pct, 0);
        expect(total).to.be.closeTo(100, 0.001);
        expect(actualMap.NVDA.price).to.equal(900);
    });

    it('getProjectedTickersFromDb returns the symbols with a saved projection (hasValuation) and an empty set otherwise', () => {
        expect(getProjectedTickersFromDb(dbPath).size).to.equal(0);
        const repo = new ProjectionRepository(dbPath);
        try {
            const projection = ProjectionSchema.parse({
                ticker: 'NVDA',
                id: '11111111-1111-4111-8111-111111111111',
                source: 'USER',
                schemaVersion: '1.2',
                version: 0,
                savedAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                name: 'Test',
                rationale: 'test',
                snapshot: { price: 100, currency: 'USD', shares: 1000, revenue: 5000, lastActualPS: 5, fiscalPeriod: 'TTM' },
                dataPreferences: { growthBasis: 'ttm', marginBasis: 'ttm' },
                scenarios: {
                    bear: { weight: 0.3, growthRate: 5, netMargin: 10, exitPE: 15, qualityMultiplier: 0.9, shareChange: 0 },
                    base: { weight: 0.4, growthRate: 10, netMargin: 15, exitPE: 20, qualityMultiplier: 1, shareChange: 0 },
                    bull: { weight: 0.3, growthRate: 15, netMargin: 20, exitPE: 25, qualityMultiplier: 1.1, shareChange: 0 },
                },
                globalSettings: { discountRate: 10, timeHorizon: 5 },
            }) as Projection;
            repo.upsertProjection(projection);
        } finally {
            repo.close();
        }
        expect([...getProjectedTickersFromDb(dbPath)]).to.deep.equal(['NVDA']);
    });
});
