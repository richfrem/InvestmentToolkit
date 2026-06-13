import { expect } from 'chai';
import fs from 'fs';
import path from 'path';
import { WatchlistService } from '../../src/services/WatchlistService';
import { WATCHLIST_FILE } from '../../src/utils/paths';

describe('WatchlistService', () => {
    let service: WatchlistService;
    const testFile = WATCHLIST_FILE;
    const backupFile = testFile + '.test.bak';

    before(() => {
        // Backup existing watchlist file
        if (fs.existsSync(testFile)) {
            fs.copyFileSync(testFile, backupFile);
        }
    });

    after(() => {
        // Restore watchlist file
        if (fs.existsSync(backupFile)) {
            fs.copyFileSync(backupFile, testFile);
            fs.unlinkSync(backupFile);
        } else if (fs.existsSync(testFile)) {
            fs.unlinkSync(testFile);
        }
    });

    beforeEach(() => {
        // Reset watchlist file to empty array
        fs.writeFileSync(testFile, JSON.stringify({ watchlist: [] }, null, 2));
        service = new WatchlistService();
    });

    it('should return empty watchlist initially', async () => {
        const list = await service.getWatchlist();
        expect(list).to.be.an('array').that.is.empty;
    });

    it('should add a ticker to watchlist', async () => {
        await service.addToWatchlist('AAPL');
        const list = await service.getWatchlist();
        expect(list).to.have.lengthOf(1);
        expect(list[0].ticker).to.equal('AAPL');
    });

    it('should not add duplicate tickers', async () => {
        await service.addToWatchlist('AAPL');
        await service.addToWatchlist('AAPL');
        const list = await service.getWatchlist();
        expect(list).to.have.lengthOf(1);
    });

    it('should remove a ticker from watchlist', async () => {
        await service.addToWatchlist('AAPL');
        await service.addToWatchlist('MSFT');
        await service.removeFromWatchlist('AAPL');
        const list = await service.getWatchlist();
        expect(list).to.have.lengthOf(1);
        expect(list[0].ticker).to.equal('MSFT');
    });
});
