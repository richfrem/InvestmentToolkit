import fs from 'fs';
import { lock } from 'proper-lockfile';
import { WATCHLIST_FILE } from '../utils/paths';

export interface WatchlistItem {
    ticker: string;
    addedAt: string;
}

export class WatchlistService {
    private async ensureFileExists(): Promise<void> {
        if (!fs.existsSync(WATCHLIST_FILE)) {
            await fs.promises.writeFile(WATCHLIST_FILE, JSON.stringify({ watchlist: [] }, null, 2));
        }
    }

    async getWatchlist(): Promise<WatchlistItem[]> {
        await this.ensureFileExists();
        try {
            const content = await fs.promises.readFile(WATCHLIST_FILE, 'utf-8');
            const data = JSON.parse(content);
            return data.watchlist || [];
        } catch (error) {
            console.error('[WatchlistService] Error reading watchlist:', error);
            return [];
        }
    }

    async addToWatchlist(ticker: string): Promise<void> {
        await this.ensureFileExists();
        const upperTicker = ticker.toUpperCase().trim();
        if (!upperTicker) return;

        let release: (() => Promise<void>) | null = null;
        try {
            release = await lock(WATCHLIST_FILE, { retries: { retries: 5, maxTimeout: 2000 } });
            const content = await fs.promises.readFile(WATCHLIST_FILE, 'utf-8');
            const data = JSON.parse(content);
            const watchlist: WatchlistItem[] = data.watchlist || [];

            if (!watchlist.some(item => item.ticker === upperTicker)) {
                watchlist.push({
                    ticker: upperTicker,
                    addedAt: new Date().toISOString()
                });
                data.watchlist = watchlist;
                await fs.promises.writeFile(WATCHLIST_FILE, JSON.stringify(data, null, 2));
            }
        } catch (error) {
            console.error(`[WatchlistService] Error adding ${ticker} to watchlist:`, error);
            throw error;
        } finally {
            if (release) {
                await release();
            }
        }
    }

    async removeFromWatchlist(ticker: string): Promise<void> {
        await this.ensureFileExists();
        const upperTicker = ticker.toUpperCase().trim();
        if (!upperTicker) return;

        let release: (() => Promise<void>) | null = null;
        try {
            release = await lock(WATCHLIST_FILE, { retries: { retries: 5, maxTimeout: 2000 } });
            const content = await fs.promises.readFile(WATCHLIST_FILE, 'utf-8');
            const data = JSON.parse(content);
            const watchlist: WatchlistItem[] = data.watchlist || [];

            const filtered = watchlist.filter(item => item.ticker !== upperTicker);
            if (filtered.length !== watchlist.length) {
                data.watchlist = filtered;
                await fs.promises.writeFile(WATCHLIST_FILE, JSON.stringify(data, null, 2));
            }
        } catch (error) {
            console.error(`[WatchlistService] Error removing ${ticker} from watchlist:`, error);
            throw error;
        } finally {
            if (release) {
                await release();
            }
        }
    }
}

export const watchlistService = new WatchlistService();
