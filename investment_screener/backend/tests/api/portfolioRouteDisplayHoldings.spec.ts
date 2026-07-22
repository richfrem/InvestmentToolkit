/**
 * portfolioRouteDisplayHoldings.spec.ts
 *
 * Wave 3 completion — GET /api/portfolio now serves enriched holdings from
 * domain_model.sqlite (account_investment/investment_price + investment.name/
 * sector/industry/pillar_id) instead of portfolio.json, and the last
 * portfolio.json sync-write (persistPortfolioWithSnapshot) is removed from
 * /sync-tv/promote and /sync-tv/apply.
 *
 * All state is tmp_path-scoped SQLite via the real repositories — never the real
 * domain_model.sqlite, never a live TradingView/yfinance call.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import {
    getHoldingsForDisplayFromDb,
    persistRefreshedPricesToDb,
} from '../../src/routes/portfolio';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('routes/portfolio.ts GET / display holdings (Wave 3 completion)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `portfolio-route-display-test-${Date.now()}-${Math.random()}.sqlite`);
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
        const now = new Date().toISOString();
        const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
        portfolioRepo.upsertAccount('TFSA', 'TFSA', 'TFSA');
        portfolioRepo.upsertAccount('RRSP', 'RRSP', 'RRSP');
        portfolioRepo.upsertAccountInvestment('TFSA', nvdaId, 3, 800, 2400, 'USD', now);
        portfolioRepo.upsertAccountInvestment('RRSP', nvdaId, 1, 800, 800, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(nvdaId, 900, 'USD', now);
        investmentRepo.close();
        portfolioRepo.close();
    }

    it('returns null on an empty db so GET / falls back to portfolio.json', () => {
        // Fresh, never-written DB (the helper creates the schema itself).
        expect(getHoldingsForDisplayFromDb(dbPath)).to.equal(null);
    });

    it('sources shares/price and enriched metadata from SQLite once populated', () => {
        seed();
        // Persist real sector/industry via the same path /refresh-prices uses.
        persistRefreshedPricesToDb(
            [{ symbol: 'NVDA', price: 900, sector: 'Technology', industry: 'Semiconductors' }],
            dbPath
        );
        const items = getHoldingsForDisplayFromDb(dbPath)!;
        expect(items).to.have.length(1);
        const nvda = items.find(i => i.symbol === 'NVDA')!;
        expect(nvda.shares).to.equal(4);          // 3 (TFSA) + 1 (RRSP)
        expect(nvda.price).to.equal(900);
        expect(nvda.sector).to.equal('Technology');
        expect(nvda.industry).to.equal('Semiconductors');
    });

    it('falls back to "Unknown" sector/industry before the first price refresh', () => {
        // Fresh TV sync: held position exists but sector/industry not resolved yet.
        seed();
        const items = getHoldingsForDisplayFromDb(dbPath)!;
        const nvda = items.find(i => i.symbol === 'NVDA')!;
        expect(nvda.sector).to.equal('Unknown');
        expect(nvda.industry).to.equal('Unknown');
    });

    it('persistRefreshedPricesToDb writes sector/industry into investment.*', () => {
        seed();
        persistRefreshedPricesToDb(
            [{ symbol: 'NVDA', price: 950, sector: 'Technology', industry: 'Semiconductors' }],
            dbPath
        );
        const investmentRepo = new InvestmentRepository(dbPath);
        const row = investmentRepo.getInvestment('NVDA')!;
        investmentRepo.close();
        expect(row.sector).to.equal('Technology');
        expect(row.industry).to.equal('Semiconductors');
    });

    it('a price-only item (no sector/industry keys) never blanks resolved metadata', () => {
        seed();
        persistRefreshedPricesToDb([{ symbol: 'NVDA', price: 900, sector: 'Technology', industry: 'Semiconductors' }], dbPath);
        // Second refresh carries only a price — sector/industry must be preserved.
        persistRefreshedPricesToDb([{ symbol: 'NVDA', price: 910 }], dbPath);
        const investmentRepo = new InvestmentRepository(dbPath);
        const row = investmentRepo.getInvestment('NVDA')!;
        investmentRepo.close();
        expect(row.sector).to.equal('Technology');
    });

    it('static guard: /sync-tv/promote and /sync-tv/apply write no portfolio.json', () => {
        const routeSrc = fs.readFileSync(
            path.resolve(__dirname, '../../src/routes/portfolio.ts'),
            'utf-8'
        );
        // persistPortfolioWithSnapshot (the JSON writer) is fully removed.
        expect(routeSrc).to.not.contain('persistPortfolioWithSnapshot');
        for (const marker of ["router.post('/sync-tv/promote'", "router.post('/sync-tv/apply'"]) {
            const start = routeSrc.indexOf(marker);
            expect(start, marker).to.be.greaterThan(-1);
            const rest = routeSrc.slice(start + marker.length);
            const end = rest.indexOf('router.post(');
            const handler = end === -1 ? rest : rest.slice(0, end);
            expect(handler, `${marker} must not write PORTFOLIO_FILE`).to.not.contain('writeFileSync(PORTFOLIO_FILE');
            expect(handler, `${marker} must persist via persistSnapshotToDb`).to.contain('persistSnapshotToDb');
        }
    });
});
