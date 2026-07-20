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
 *   - investment_screener/backend/data/watchlist.json (Reads watchlist array — read side
 *     stays on JSON until Task 11's watchlist-consumer cutover)
 *
 * Key Output Dependencies:
 *   - investment_screener/backend/data/domain_model.sqlite (Wave 2 Task 9.4 producer
 *     cutover: addToWatchlist/removeFromWatchlist now write `investment.is_watchlisted`
 *     / `investment.watchlist_added_at` via InvestmentRepository instead of rewriting
 *     watchlist.json in place. watchlist.json itself is intentionally left untouched by
 *     this write path — the read side (getWatchlist) still serves it, so this is a
 *     necessarily transitional state within Wave 2, not a bug: full parity returns once
 *     Task 11 cuts the read side over too.)
 */

import fs from 'fs';
import { InvestmentRepository } from './InvestmentRepository';
import { DOMAIN_MODEL_DB_FILE, WATCHLIST_FILE } from '../utils/paths';


export interface WatchlistItem {
    ticker: string;
    addedAt: string;
}

export class WatchlistService {
    private dbPath: string;

    constructor(dbPath: string = DOMAIN_MODEL_DB_FILE) {
        this.dbPath = dbPath;
    }

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
