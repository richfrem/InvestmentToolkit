/**
 * WatchlistService.ts - Watchlist data store persistence and operations manager.
 *
 * Purpose:
 *   Handles operations on the user's ticker watchlist including checking, adding, and removing items.
 *   Implements file locking to guard against concurrent edit corruption.
 *
 * Layer:
 *   Backend / Services / Data Persistence
 *
 * Usage Examples:
 *   const list = await watchlistService.getWatchlist();
 *   await watchlistService.addToWatchlist('MSFT');
 *
 * Key Functions (Index):
 *   - ensureFileExists() - Creates a blank watchlist structure if missing
 *   - getWatchlist() - Reads all watchlist items
 *   - addToWatchlist(ticker: string) - Appends a ticker if not already present
 *   - removeFromWatchlist(ticker: string) - Deletes a ticker from the list
 *
 * Key Input Dependencies:
 *   - investment_screener/backend/data/domain_model.sqlite (Wave 2 Task 10/11 read-path
 *     cutover: getWatchlist() now reads `investment.is_watchlisted` /
 *     `investment.watchlist_added_at` via InvestmentRepository.listWatchlisted()
 *     instead of watchlist.json. Verified byte-identical ticker set and addedAt
 *     timestamps against watchlist.json before the cutover — see
 *     InvestmentRepository.ts's module docstring. watchlist.json itself is left
 *     untouched on disk, unmodified and unread by this service now.)
 *
 * Key Output Dependencies:
 *   - investment_screener/backend/data/domain_model.sqlite (Wave 2 Task 9.4 producer
 *     cutover: addToWatchlist/removeFromWatchlist write `investment.is_watchlisted`
 *     / `investment.watchlist_added_at` via InvestmentRepository)
 */

import { InvestmentRepository } from './InvestmentRepository';
import { DOMAIN_MODEL_DB_FILE } from '../utils/paths';


export interface WatchlistItem {
    ticker: string;
    addedAt: string;
}

export class WatchlistService {
    private dbPath: string;

    constructor(dbPath: string = DOMAIN_MODEL_DB_FILE) {
        this.dbPath = dbPath;
    }

    async getWatchlist(): Promise<WatchlistItem[]> {
        const repo = new InvestmentRepository(this.dbPath);
        try {
            return repo.listWatchlisted();
        } catch (error) {
            console.error('[WatchlistService] Error reading watchlist:', error);
            return [];
        } finally {
            repo.close();
        }
    }

    async addToWatchlist(ticker: string): Promise<void> {
        const upperTicker = ticker.toUpperCase().trim();
        if (!upperTicker) return;

        const repo = new InvestmentRepository(this.dbPath);
        try {
            const existing = repo.getInvestment(upperTicker);
            if (existing?.is_watchlisted) return;
            repo.setWatchlisted(upperTicker, true, new Date().toISOString());
        } catch (error) {
            console.error(`[WatchlistService] Error adding ${ticker} to watchlist:`, error);
            throw error;
        } finally {
            repo.close();
        }
    }

    async removeFromWatchlist(ticker: string): Promise<void> {
        const upperTicker = ticker.toUpperCase().trim();
        if (!upperTicker) return;

        const repo = new InvestmentRepository(this.dbPath);
        try {
            repo.setWatchlisted(upperTicker, false, null);
        } catch (error) {
            console.error(`[WatchlistService] Error removing ${ticker} from watchlist:`, error);
            throw error;
        } finally {
            repo.close();
        }
    }
}

export const watchlistService = new WatchlistService();
