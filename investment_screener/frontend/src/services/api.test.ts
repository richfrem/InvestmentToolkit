/**
 * api.test.ts (syncAndRefreshPortfolio)
 *
 * Purpose:
 *     Regression coverage for the 2026-07-27 "Refresh button doesn't update
 *     prices" bug. syncAndRefreshPortfolio() previously only called
 *     refreshPrices() (the actual price-fetch endpoint) as an exception
 *     fallback when syncPortfolio() (position/share sync, which never writes
 *     prices — see BrokerSyncService.ts) threw. On the normal success path,
 *     refreshPrices() was never called at all, so displayed prices never
 *     updated no matter how many times any "Refresh" button (Portfolio
 *     Summary, Table, Heatmap — they all call this one function) was clicked.
 *
 * Layer: Frontend / Services (vitest)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { syncAndRefreshPortfolio } from './api';

describe('syncAndRefreshPortfolio', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('calls refreshPrices even when syncPortfolio succeeds — prices must always refresh', async () => {
        const fetchMock = vi.fn(async (url: string) => {
            if (url === '/api/portfolio/sync-tv/apply') {
                return { ok: true, json: async () => ({ success: true, positionCount: 23 }) } as Response;
            }
            if (url === '/api/portfolio/refresh-prices') {
                return { ok: true, json: async () => ({ success: true, updated: 23, heatmap: {} }) } as Response;
            }
            throw new Error(`Unexpected fetch: ${url}`);
        });
        vi.stubGlobal('fetch', fetchMock);

        const result = await syncAndRefreshPortfolio();

        const calledUrls = fetchMock.mock.calls.map((c) => c[0]);
        expect(calledUrls).toContain('/api/portfolio/sync-tv/apply');
        expect(calledUrls).toContain('/api/portfolio/refresh-prices');
        expect(result.success).toBe(true);
    });

    it('still calls refreshPrices when syncPortfolio throws (position sync down, prices must still try)', async () => {
        const fetchMock = vi.fn(async (url: string) => {
            if (url === '/api/portfolio/sync-tv/apply') {
                return { ok: false, json: async () => ({ error: 'TV unreachable' }) } as Response;
            }
            if (url === '/api/portfolio/refresh-prices') {
                return { ok: true, json: async () => ({ success: true, updated: 10, heatmap: {} }) } as Response;
            }
            throw new Error(`Unexpected fetch: ${url}`);
        });
        vi.stubGlobal('fetch', fetchMock);

        const result = await syncAndRefreshPortfolio();

        const calledUrls = fetchMock.mock.calls.map((c) => c[0]);
        expect(calledUrls).toContain('/api/portfolio/refresh-prices');
        expect(result.success).toBe(true);
        expect(result.dataSource).toBe('yfinance');
    });

    it('reports failure only when both position sync and price refresh fail', async () => {
        const fetchMock = vi.fn(async () => ({ ok: false, json: async () => ({ error: 'down' }) } as Response));
        vi.stubGlobal('fetch', fetchMock);

        const result = await syncAndRefreshPortfolio();

        expect(result.success).toBe(false);
        expect(result.dataSource).toBe('none');
    });

    it('says prices were not updated when only the position sync worked, and why', async () => {
        const fetchMock = vi.fn(async (url: string) => {
            if (url === '/api/portfolio/sync-tv/apply') {
                return { ok: true, json: async () => ({ success: true, positionCount: 28 }) } as Response;
            }
            return { ok: false, json: async () => ({ error: 'TradingView Desktop is not connected' }) } as Response;
        });
        vi.stubGlobal('fetch', fetchMock);

        const result = await syncAndRefreshPortfolio();

        expect(result.success).toBe(true);        // positions did sync
        expect(result.pricesOk).toBe(false);      // but the total did not refresh
        expect(result.message).toContain('price refresh failed: TradingView Desktop is not connected');
    });

    it('lists the tickers that could not be quoted and does not call the prices ok', async () => {
        const fetchMock = vi.fn(async (url: string) => {
            if (url === '/api/portfolio/sync-tv/apply') {
                return { ok: true, json: async () => ({ success: true, positionCount: 28 }) } as Response;
            }
            return { ok: true, json: async () => ({ success: true, updated: 80, missingPrices: ['NBIS', 'MU'], heatmap: {} }) } as Response;
        });
        vi.stubGlobal('fetch', fetchMock);

        const result = await syncAndRefreshPortfolio();

        expect(result.pricesOk).toBe(false);
        expect(result.missing).toEqual(['NBIS', 'MU']);
        expect(result.message).toContain('2 not quoted');
    });

    it('calls the prices ok only when every ticker was quoted', async () => {
        const fetchMock = vi.fn(async (url: string) => {
            if (url === '/api/portfolio/sync-tv/apply') {
                return { ok: true, json: async () => ({ success: true, positionCount: 28 }) } as Response;
            }
            return { ok: true, json: async () => ({ success: true, updated: 88, missingPrices: [], heatmap: {} }) } as Response;
        });
        vi.stubGlobal('fetch', fetchMock);

        expect((await syncAndRefreshPortfolio()).pricesOk).toBe(true);
    });
});

