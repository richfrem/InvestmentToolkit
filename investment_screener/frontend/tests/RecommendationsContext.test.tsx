/**
 * @vitest-environment jsdom
 * Purpose: verify every mounted consumer receives the same fetched snapshot and refresh.
 * Layer: Frontend integration. Key Functions: Consumer; real HTTP server lifecycle and tests.
 * Key input dependencies: React, jsdom, a temporary local HTTP server (no mocked responses).
 */
import React from 'react';
import { createServer } from 'node:http';
import type { Server } from 'node:http';
import { afterAll, beforeAll, expect, it } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { RecommendationsProvider } from '../src/contexts/RecommendationsContext';
import { useRecommendations } from '../src/contexts/useRecommendations';

let server: Server;
let origin: string;
let action = 'WATCHLIST';
let requests = 0;
let failing = false;
const nativeFetch = globalThis.fetch;

function Consumer({ name }: { name: string }) {
    const records = useRecommendations();
    return <div data-testid={name}>{records.TEST?.action ?? 'Unavailable'}</div>;
}

beforeAll(async () => {
    server = createServer((request, response) => {
        expect(request.url).toBe('/api/screener/recommendations');
        requests++;
        response.writeHead(failing ? 503 : 200, { 'Content-Type': 'application/json' });
        response.end(JSON.stringify({ TEST: { ticker: 'TEST', action } }));
    });
    await new Promise<void>((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });
    const address = server.address();
    if (!address || typeof address === 'string') throw new Error('Missing test server address');
    origin = `http://127.0.0.1:${address.port}`;
    // Browser-relative URL resolution; the request still goes through real HTTP.
    globalThis.fetch = (input, init) => nativeFetch(new URL(String(input), origin), init);
});

afterAll(async () => {
    cleanup();
    globalThis.fetch = nativeFetch;
    if (!server.listening) return;
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
});

it('shares one fetch, refreshes both surfaces, and shows unavailable on failure', async () => {
    render(<RecommendationsProvider><Consumer name="table" /><Consumer name="analysis" /></RecommendationsProvider>);
    await waitFor(() => expect(screen.getByTestId('table').textContent).toBe('WATCHLIST'));
    expect(screen.getByTestId('analysis').textContent).toBe('WATCHLIST');
    expect(requests).toBe(1);
    action = 'TRIM';
    window.dispatchEvent(new Event('recommendation-data-changed'));
    await waitFor(() => expect(screen.getByTestId('table').textContent).toBe('TRIM'));
    expect(screen.getByTestId('analysis').textContent).toBe('TRIM');
    failing = true;
    window.dispatchEvent(new Event('recommendation-data-changed'));
    await waitFor(() => expect(screen.getByTestId('table').textContent).toBe('Unavailable'));
    expect(screen.getByTestId('analysis').textContent).toBe('Unavailable');
});
