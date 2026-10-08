/**
 * @vitest-environment jsdom
 * Purpose: verify Daily Brief cards filter by the current canonical recommendation.
 * Layer: Frontend integration. Key Functions: server lifecycle, filter interaction test.
 * Key Input Dependencies: real HTTP brief fixture, React recommendation context, jsdom.
 */
import React from 'react';
import { createServer } from 'node:http';
import type { Server } from 'node:http';
import { JSDOM } from 'jsdom';
import { afterAll, beforeAll, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import DailyBriefPage from '../src/pages/DailyBriefPage';
import { HelpModalProvider } from '../src/components/HelpModal';
import { DeepDiveModal } from '../src/components/DeepDiveModal';
import ValuationModeler from '../src/components/ValuationModeler';
import { RecommendationsContext } from '../src/contexts/useRecommendations';
import type { RecommendationRecord, StockData } from '../src/services/api';

let server: Server;
const nativeFetch = globalThis.fetch;
const storageDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
const actions = { MU: 'TRIM', SHAZ: 'ACCUMULATE', INTC: 'INITIATE', KEEP: 'MAINTAIN', WAIT: 'WATCHLIST' };
const records = Object.fromEntries(Object.entries(actions).map(([ticker, action]) =>
    [ticker, { ticker, action, reason: `${ticker} current reason` } as RecommendationRecord]));
const savedProjection = {
    ticker: 'APLD', id: 'saved-apld', source: 'AI_AGENT', version: 12,
    savedAt: '2026-10-07T12:00:00Z', updatedAt: '2026-10-07T12:00:00Z', name: 'Saved APLD',
    snapshot: { price: 25.34, revenue: 611311000, shares: 302387140 },
    globalSettings: { discountRate: 12.77, timeHorizon: 5 },
    aiThesis: { action: 'MAINTAIN', fairValue: 27.67, model: '5yr_dcf_scenarios', rationale: 'Saved analysis' },
    scenarios: {
        bear: { weight: 0.2, growthRate: 24, netMargin: 8, exitPE: 15, qualityMultiplier: 0.9, shareChange: 5, scenarioPrice: 2.75 },
        base: { weight: 0.52, growthRate: 35, netMargin: 18, exitPE: 28, qualityMultiplier: 1, shareChange: 3.5, scenarioPrice: 21.09 },
        bull: { weight: 0.28, growthRate: 45, netMargin: 25, exitPE: 35, qualityMultiplier: 1.05, shareChange: 2.5, scenarioPrice: 57.7 },
    },
};

beforeAll(async () => {
    // A real browser Storage instance avoids Node 26's optional Web Storage API.
    const browserStorage = new JSDOM('', { url: 'http://localhost' }).window.localStorage;
    Object.defineProperty(globalThis, 'localStorage', { value: browserStorage, configurable: true });
    server = createServer((_request, response) => {
        response.writeHead(200, { 'Content-Type': 'application/json' });
        if (_request.url?.startsWith('/api/projections/APLD')) {
            response.end(JSON.stringify([savedProjection]));
            return;
        }
        if (_request.url?.startsWith('/api/research/')) {
            response.end(JSON.stringify({ filename: 'APLD_2026-10-07.md',
                content: '# APLD research\nUse **WACC** for DCF. [WACC source](https://example.org/source)',
            }));
            return;
        }
        response.end(JSON.stringify({
            date: '2026-10-04', timestamp: '2026-10-04T12:00:00Z',
            macro_regime: { regime: 'NEUTRAL', score: 0, vix: 20, details: [] },
            conviction_scores: [], score_deltas: {}, pillar_health: [], pillar_deltas: {}, earnings_flags: [],
            recommendations: [...Object.keys(actions), 'UNKNOWN'].map((ticker, index) => ({
                ticker, recommendation: 'TRIM', signal: 'TRIM', score: 0, held: true,
                rationale: 'Saved opinion', actionable: false, urgency: index + 1,
                standingDecision: null, earnings: null, proposedTrade: null,
            })),
        }));
    });
    await new Promise<void>((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });
    const address = server.address();
    if (!address || typeof address === 'string') throw new Error('Missing fixture server address');
    const origin = `http://127.0.0.1:${address.port}`;
    globalThis.fetch = (input, init) => nativeFetch(new URL(String(input), origin), init);
});

afterAll(async () => {
    cleanup();
    globalThis.fetch = nativeFetch;
    if (storageDescriptor) Object.defineProperty(globalThis, 'localStorage', storageDescriptor);
    if (server?.listening) await new Promise<void>(resolve => server.close(() => resolve()));
});

it('filters cards using current actions, keeps correct counts, and restores all cards', async () => {
    render(<HelpModalProvider><RecommendationsContext.Provider value={records}><DailyBriefPage /></RecommendationsContext.Provider></HelpModalProvider>);
    const cards = await screen.findByRole('region', { name: 'Recommendations' });
    const filters = within(cards).getByRole('group', { name: 'Recommendation filters' });
    for (const [ticker, action] of Object.entries(actions)) {
        const button = within(filters).getByRole('button', { name: new RegExp(`${action}.*1`, 'i') });
        fireEvent.click(button);
        expect(button.getAttribute('aria-pressed')).toBe('true');
        expect(within(cards).getByText(ticker)).toBeTruthy();
        for (const other of Object.keys(actions).filter(name => name !== ticker)) {
            expect(within(cards).queryByText(other)).toBeNull();
        }
        expect(within(cards).queryByText('UNKNOWN')).toBeNull();
    }
    fireEvent.click(within(filters).getByRole('button', { name: /exit.*0/i }));
    expect(within(cards).getByText('No recommendations match this filter.')).toBeTruthy();
    fireEvent.click(within(filters).getByRole('button', { name: /all.*6/i }));
    for (const ticker of [...Object.keys(actions), 'UNKNOWN']) expect(within(cards).getByText(ticker)).toBeTruthy();
});

it('opens help from formatted research text while preserving source links', async () => {
    cleanup();
    render(<HelpModalProvider><DeepDiveModal isOpen onClose={() => {}} filename="APLD_2026-10-07.md" /></HelpModalProvider>);
    await screen.findByRole('heading', { name: 'APLD research' });
    expect(screen.getByRole('link', { name: 'WACC source' }).getAttribute('href')).toBe('https://example.org/source');
    fireEvent.click(screen.getByRole('button', { name: 'WACC' }));
    expect(screen.getByRole('dialog', { name: 'WACC (Weighted Average Cost of Capital)' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'APLD research' })).toBeTruthy();
});

it('keeps the saved rate and report separate from an edited what-if rate', async () => {
    cleanup();
    localStorage.clear();
    const stockData = { symbol: 'APLD', price: 25.34, currency: 'USD', metrics: {
        revenue: 611311000, shares_diluted: 299000000, shares_outstanding: 302387140,
        market_cap: 7600000000, profit_margin: 0.18,
    } } as unknown as StockData;
    render(<HelpModalProvider><ValuationModeler stockData={stockData} /></HelpModalProvider>);
    await screen.findByText(/Saved rate: 12.77%/);
    const rateInputs = screen.getAllByDisplayValue('12.77');
    fireEvent.change(rateInputs.find(input => input.getAttribute('type') === 'number')!, { target: { value: '15' } });
    expect(screen.getByText(/Editor rate is a what-if assumption/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /View Full Report/i }));
    expect(await screen.findByText('Discount Rate: 12.77%')).toBeTruthy();
    expect(screen.getByText('$21.09')).toBeTruthy();
});
