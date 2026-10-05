/**
 * @vitest-environment jsdom
 * Purpose: verify Daily Brief cards filter by the current canonical recommendation.
 * Layer: Frontend integration. Key Functions: server lifecycle, filter interaction test.
 * Key Input Dependencies: real HTTP brief fixture, React recommendation context, jsdom.
 */
import React from 'react';
import { createServer } from 'node:http';
import type { Server } from 'node:http';
import { afterAll, beforeAll, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import DailyBriefPage from '../src/pages/DailyBriefPage';
import { RecommendationsContext } from '../src/contexts/useRecommendations';
import type { RecommendationRecord } from '../src/services/api';

let server: Server;
const nativeFetch = globalThis.fetch;
const actions = { MU: 'TRIM', SHAZ: 'ACCUMULATE', INTC: 'INITIATE', KEEP: 'MAINTAIN', WAIT: 'WATCHLIST' };
const records = Object.fromEntries(Object.entries(actions).map(([ticker, action]) =>
    [ticker, { ticker, action, reason: `${ticker} current reason` } as RecommendationRecord]));

beforeAll(async () => {
    server = createServer((_request, response) => {
        response.writeHead(200, { 'Content-Type': 'application/json' });
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
    if (server?.listening) await new Promise<void>(resolve => server.close(() => resolve()));
});

it('filters cards using current actions, keeps correct counts, and restores all cards', async () => {
    render(<RecommendationsContext.Provider value={records}><DailyBriefPage /></RecommendationsContext.Provider>);
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
