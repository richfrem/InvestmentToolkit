/**
 * @vitest-environment jsdom
 * Purpose: a Daily Brief card states one stance, and a stale top card asks for a refresh first.
 * Layer: Frontend integration. Key Functions: single-stance chip test, refresh-first chip test.
 * Key Input Dependencies: real HTTP brief fixture shaped like brief_recommendations.py, jsdom.
 */
import { createServer } from 'node:http';
import type { Server } from 'node:http';
import { JSDOM } from 'jsdom';
import { afterAll, beforeAll, expect, it } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import DailyBriefPage from '../src/pages/DailyBriefPage';
import { HelpModalProvider } from '../src/components/HelpModal';
import { RecommendationsContext } from '../src/contexts/useRecommendations';
import type { RecommendationRecord } from '../src/services/api';

let server: Server;
const nativeFetch = globalThis.fetch;
const storageDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
const note = "You decided 'hold no add' today, so the stance is hold and no trade is proposed.";
// The valuation action is ACCUMULATE, but the owner's decision set today makes the stance MAINTAIN.
const records = { SPCX: { ticker: 'SPCX', action: 'ACCUMULATE', reason: 'Below fair value',
    decision_check: { relation: 'CONFIRMED', effective: 'MAINTAIN', note, age_days: 0 } } as RecommendationRecord };

beforeAll(async () => {
    const browserStorage = new JSDOM('', { url: 'http://localhost' }).window.localStorage;
    Object.defineProperty(globalThis, 'localStorage', { value: browserStorage, configurable: true });
    server = createServer((_request, response) => {
        response.writeHead(200, { 'Content-Type': 'application/json' });
        response.end(JSON.stringify({
            date: '2026-10-08', timestamp: '2026-10-08T12:00:00Z',
            macro_regime: { regime: 'NEUTRAL', score: 0, vix: 20, details: [] },
            conviction_scores: [], score_deltas: {}, pillar_health: [], pillar_deltas: {}, earnings_flags: [],
            recommendations: [{
                ticker: 'SPCX', recommendation: 'MAINTAIN', signal: 'ACCUMULATE', score: 2, held: true,
                rationale: `${note} For reference only, the valuation model rates it a buy, +219.0% to fair value.`,
                actionable: false, urgency: 1, executionStatus: 'BLOCKED', standingDecision: null, earnings: null, proposedTrade: null,
                priority: { tier: 2, label: 'Holding by your decision' },
                decisionCheck: { relation: 'CONFIRMED', effective: 'MAINTAIN', note },
                refreshFirst: { command: '/update-stock-analysis SPCX', reasons: ['Valuation saved 37 days ago'] },
            }],
        }));
    });
    await new Promise<void>((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
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

it('shows one stance on a card held by the owner decision, never a second action label', async () => {
    render(<HelpModalProvider><RecommendationsContext.Provider value={records}><DailyBriefPage /></RecommendationsContext.Provider></HelpModalProvider>);
    const cards = await screen.findByRole('region', { name: 'Recommendations' });
    const card = within(cards).getByText('SPCX').closest('div.flex-col') as HTMLElement;
    expect(within(card).getByText('MAINTAIN')).toBeTruthy();
    expect(within(card).queryByText(/ACCUMULATE/)).toBeNull();     // was "signal ACCUMULATE +2" beside MAINTAIN
    expect(within(card).queryByText(/signal/i)).toBeNull();
    expect(within(card).getByText('Holding by your decision')).toBeTruthy();
});

it('asks for a refresh before acting when a top card rests on a stale valuation', async () => {
    const cards = await screen.findByRole('region', { name: 'Recommendations' });
    expect(within(cards).getByRole('button', { name: /Refresh the analysis first: \/update-stock-analysis SPCX/ })).toBeTruthy();
    expect(within(cards).getByText('Valuation saved 37 days ago')).toBeTruthy();
});
