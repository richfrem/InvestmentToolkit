import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { WatchlistService } from '../../src/services/WatchlistService';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('WatchlistService', () => {
    let service: WatchlistService;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `watchlist-service-test-${Date.now()}-${Math.random()}.sqlite`);
        service = new WatchlistService(dbPath);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    // Wave 2 Task 9.4 producer cutover: addToWatchlist/removeFromWatchlist now
    // write investment.is_watchlisted / investment.watchlist_added_at in
    // domain_model.sqlite via InvestmentRepository, instead of rewriting
    // watchlist.json in place. getWatchlist() (the read side) stays on
    // watchlist.json until Task 11 — not exercised here.

    it('marks a ticker as watchlisted in sqlite', async () => {
        await service.addToWatchlist('AAPL');

        const repo = new InvestmentRepository(dbPath);
        const row = repo.getInvestment('AAPL');
        repo.close();

        expect(row).to.not.be.null;
        expect(row!.is_watchlisted).to.equal(1);
        expect(row!.watchlist_added_at).to.be.a('string');
    });

    it('is idempotent — adding the same ticker twice does not reset watchlist_added_at', async () => {
        await service.addToWatchlist('AAPL');
        const repo1 = new InvestmentRepository(dbPath);
        const firstAddedAt = repo1.getInvestment('AAPL')!.watchlist_added_at;
        repo1.close();

        await new Promise(resolve => setTimeout(resolve, 5));
        await service.addToWatchlist('AAPL');

        const repo2 = new InvestmentRepository(dbPath);
        const secondAddedAt = repo2.getInvestment('AAPL')!.watchlist_added_at;
        repo2.close();

        expect(secondAddedAt).to.equal(firstAddedAt);
    });

    it('removes a ticker from the watchlist (is_watchlisted=0)', async () => {
        await service.addToWatchlist('AAPL');
        await service.removeFromWatchlist('AAPL');

        const repo = new InvestmentRepository(dbPath);
        const row = repo.getInvestment('AAPL');
        repo.close();

        expect(row!.is_watchlisted).to.equal(0);
        expect(row!.watchlist_added_at).to.be.null;
    });

    it('creates the investment row if it does not already exist', async () => {
        const repo0 = new InvestmentRepository(dbPath);
        expect(repo0.getInvestment('NEWTICKER')).to.be.null;
        repo0.close();

        await service.addToWatchlist('NEWTICKER');

        const repo = new InvestmentRepository(dbPath);
        const row = repo.getInvestment('NEWTICKER');
        repo.close();
        expect(row).to.not.be.null;
        expect(row!.is_watchlisted).to.equal(1);
    });
});
