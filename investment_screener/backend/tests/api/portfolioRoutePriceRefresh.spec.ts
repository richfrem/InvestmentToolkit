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
import {
    persistRefreshedPricesToDb,
    getPortfolioTotalUsdFromDb,
    getWatchlistTickersForRefresh,
    clearPricesBeforeRefresh,
} from '../../src/routes/portfolio';
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

    it('the /refresh-prices handler is SQLite-only: no portfolio.json write remains', () => {
        // Static guard: proves the JSON write was genuinely removed from this path
        // (the full route can't be exercised here — it spawns live python/yfinance,
        // forbidden in this worktree). The handler must persist via
        // persistRefreshedPricesToDb and must NOT call persistPortfolioWithSnapshot
        // (the JSON writer) or write PORTFOLIO_FILE.
        const routeSrc = fs.readFileSync(
            path.resolve(__dirname, '../../src/routes/portfolio.ts'),
            'utf-8'
        );
        const marker = "router.post('/refresh-prices'";
        const start = routeSrc.indexOf(marker);
        expect(start).to.be.greaterThan(-1);
        // Handler body runs until the next route registration.
        const rest = routeSrc.slice(start + marker.length);
        const end = rest.indexOf('router.post(');
        const handler = end === -1 ? rest : rest.slice(0, end);
        expect(handler).to.contain('persistRefreshedPricesToDb');
        expect(handler).to.not.contain('persistPortfolioWithSnapshot');
        expect(handler).to.not.contain('writeFileSync');
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

    // Regression coverage for the 2026-07-27 bug: /refresh-prices only ever
    // refreshed held positions, so watchlist-only tickers (is_watchlisted=1,
    // no shares) went stale indefinitely. getWatchlistTickersForRefresh()
    // must surface them, shaped so fetch_portfolio_heatmap.py and
    // persistRefreshedPricesToDb can process them like any other item.
    describe('getWatchlistTickersForRefresh', () => {
        it('returns watchlist-only tickers as shares:0 refresh items', () => {
            const investmentRepo = new InvestmentRepository(dbPath);
            investmentRepo.setWatchlisted('OKLO', true, new Date().toISOString());
            investmentRepo.setWatchlisted('CEG', true, new Date().toISOString());
            investmentRepo.close();

            const items = getWatchlistTickersForRefresh(dbPath);
            const symbols = items.map((i) => i.symbol).sort();
            expect(symbols).to.deep.equal(['CEG', 'OKLO']);
            expect(items.every((i) => i.shares === 0)).to.equal(true);
        });

        it('returns an empty array when nothing is watchlisted', () => {
            // Touch the DB so the investment table exists, then assert empty.
            const investmentRepo = new InvestmentRepository(dbPath);
            investmentRepo.close();
            expect(getWatchlistTickersForRefresh(dbPath)).to.deep.equal([]);
        });
    });

    // Regression coverage: a symbol whose refresh fetch fails/is skipped must
    // read as missing afterward, not silently keep serving yesterday's price.
    describe('clearPricesBeforeRefresh', () => {
        it('deletes investment_price rows for the given symbols before a refresh fetch', () => {
            seedStale(); // NVDA priced @ 800
            const investmentRepo = new InvestmentRepository(dbPath);
            const portfolioRepo = new PortfolioRepository(dbPath);
            const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
            expect(portfolioRepo.getInvestmentPrice(nvdaId)).to.not.equal(null);

            clearPricesBeforeRefresh(['NVDA'], dbPath);

            expect(portfolioRepo.getInvestmentPrice(nvdaId)).to.equal(null);
            investmentRepo.close();
            portfolioRepo.close();
        });

        it('leaves prices for symbols NOT in the refresh set untouched', () => {
            seedStale();
            const investmentRepo = new InvestmentRepository(dbPath);
            const portfolioRepo = new PortfolioRepository(dbPath);
            const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');

            clearPricesBeforeRefresh(['AAPL'], dbPath); // unrelated symbol

            expect(portfolioRepo.getInvestmentPrice(nvdaId)).to.not.equal(null);
            investmentRepo.close();
            portfolioRepo.close();
        });
    });
});
