/**
 * portfolioRoutePriceRefresh.spec.ts
 *
 * Purpose: guards the /refresh-prices route. Every refresh in the app and in the
 * tv-price-refresh skill mode is one implementation: investment_screener/backend/py_services/
 * tv_price_refresh.py (scope from SQLite, TradingView quotes, repository writes). The route only
 * runs it and reports; it must not carry a second price writer or a second price source.
 * The script itself is covered by tests/py_services/test_tv_price_refresh.py.
 *
 * All state is tmp_path-scoped SQLite seeded via the real repository functions, never the real
 * domain_model.sqlite, never a live TradingView call.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { getPortfolioTotalUsdFromDb } from '../../src/routes/portfolio';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

function handlerSource(): string {
    const routeSrc = fs.readFileSync(path.resolve(__dirname, '../../src/routes/portfolio.ts'), 'utf-8');
    const start = routeSrc.indexOf("router.post('/refresh-prices'");
    expect(start).to.be.greaterThan(-1);
    const rest = routeSrc.slice(start + 1);
    const end = rest.indexOf('router.post(');
    return end === -1 ? rest : rest.slice(0, end);
}

describe('routes/portfolio.ts /refresh-prices -> the shared Python refresh', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `portfolio-route-pricerefresh-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('the handler runs tv_price_refresh.py and writes nothing itself', () => {
        const handler = handlerSource();
        expect(handler).to.contain("spawnPythonScript('tv_price_refresh.py'");
        expect(handler).to.not.contain('fetch_portfolio_heatmap');
        expect(handler).to.not.contain('persistPortfolioWithSnapshot');
        expect(handler).to.not.contain('writeFileSync');
        expect(handler).to.not.match(/upsertInvestmentPrice|Repository\(/);
    });

    it('prices come from TradingView only, and an unquoted symbol is reported not cleared', () => {
        const handler = handlerSource();
        expect(handler).to.contain('isTradingViewConnected');
        expect(handler).to.contain('503');
        expect(handler).to.contain('missingPrices');
        expect(handler).to.not.match(/yfinance|Yahoo/i);
        expect(handler).to.not.contain('clearPricesBeforeRefresh');
    });

    it('a stale cached bridge result is an error, never reported as a refresh', () => {
        const handler = handlerSource();
        expect(handler).to.contain('result.stale');
        expect(handler).to.contain('502');
    });

    it('portfolio totals read the price row the refresh wrote', () => {
        const investmentRepo = new InvestmentRepository(dbPath);
        const portfolioRepo = new PortfolioRepository(dbPath);
        const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
        const now = new Date().toISOString();
        portfolioRepo.upsertAccount('TFSA', 'TFSA', 'TFSA');
        portfolioRepo.upsertAccountInvestment('TFSA', nvdaId, 4, 800, 3200, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(nvdaId, 800, 'USD', now);
        expect(getPortfolioTotalUsdFromDb(dbPath)).to.equal(3200);
        portfolioRepo.upsertInvestmentPrice(nvdaId, 950, 'USD', now);
        expect(getPortfolioTotalUsdFromDb(dbPath)).to.equal(3800);
        investmentRepo.close();
        portfolioRepo.close();
    });
});
