/**
 * portfolioRoutePriceRefresh.spec.ts
 *
 * Purpose: proves routes/portfolio.ts's /refresh-prices persistence path is now
 * SQLite-only. The previously-missing capability was that a live price refresh had
 * NO path to persist freshly-fetched prices into `investment_price` — only the
 * one-time migrate_portfolio_to_sqlite.py ever wrote that table, so SQLite prices
 * went permanently stale after the initial migration.
 *
 * `persistRefreshedPricesToDb(items, dbPath)` is the exported unit that closes this
 * gap: given the flat `updatedItems` array /refresh-prices builds (fresh live
 * prices per symbol), it upserts one `investment_price` row per symbol so a
 * subsequent getPortfolioTotalValue()/getAccountMarketValues() reflects the fresh
 * price, not a stale migration-era one.
 *
 * All state is tmp_path-scoped SQLite seeded via the real repository functions —
 * never the real domain_model.sqlite, never a live TradingView/yfinance call.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { persistRefreshedPricesToDb, getPortfolioTotalUsdFromDb } from '../../src/routes/portfolio';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('routes/portfolio.ts /refresh-prices -> SQLite-only price persistence', () => {
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

    /** Seed a held position with a STALE migration-era price, mimicking the real
     * post-migrate_portfolio_to_sqlite.py state /refresh-prices must update. */
    function seedStale() {
        const investmentRepo = new InvestmentRepository(dbPath);
        const portfolioRepo = new PortfolioRepository(dbPath);
        const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
        const now = new Date().toISOString();
        portfolioRepo.upsertAccount('TFSA', 'TFSA', 'TFSA');
        portfolioRepo.upsertAccountInvestment('TFSA', nvdaId, 4, 800, 3200, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(nvdaId, 800, 'USD', now); // stale
        investmentRepo.close();
        portfolioRepo.close();
    }

    it('persists a freshly-refreshed price into investment_price (not the stale one)', () => {
        seedStale();
        // Before refresh: 4 NVDA @ 800 = 3200
        expect(getPortfolioTotalUsdFromDb(dbPath)).to.equal(3200);

        // /refresh-prices-shaped flat items array (fresh live price)
        const updatedItems = [
            { symbol: 'NVDA', shares: 4, book_price: 800, price: 950, last_updated: new Date().toISOString() },
        ];
        const count = persistRefreshedPricesToDb(updatedItems, dbPath);
        expect(count).to.equal(1);

        // After refresh: 4 NVDA @ 950 = 3800 — proves the fresh price is now the
        // one SQLite reads, closing the "prices go stale forever" gap.
        expect(getPortfolioTotalUsdFromDb(dbPath)).to.equal(3800);
    });

    it('skips USD_CASH and non-numeric/non-positive prices without throwing', () => {
        seedStale();
        const count = persistRefreshedPricesToDb(
            [
                { symbol: 'USD_CASH', shares: 100, price: 1 },
                { symbol: 'AMD', shares: 5, price: null },
                { symbol: 'INTC', shares: 5, price: 0 },
                { symbol: 'NVDA', shares: 4, price: 950 },
            ],
            dbPath
        );
        expect(count).to.equal(1); // only NVDA had a usable fresh price
    });
});
