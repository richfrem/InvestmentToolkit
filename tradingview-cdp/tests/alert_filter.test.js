/**
 * alert_filter.test.js - Jest tests for the alert list --filter symbol source.
 *
 * Purpose:
 *   The portfolio and watchlist symbols come from the backend's SQLite-backed endpoints
 *   (sent with the local API token); an unreachable or failing backend is an explicit
 *   error, never an empty filter; cli.js reads no portfolio file and prints no debug line.
 *
 * Key Input Dependencies:
 *   - ../core/alert_filter.js, ../cli.js (read as text)
 */

import { describe, it, expect } from '@jest/globals';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { normalizeSymbol, loadFilterSymbols, readApiToken } from '../core/alert_filter.js';

const here = dirname(fileURLToPath(import.meta.url));

function fakeFetch(routes) {
  const calls = [];
  const fn = async (url, init = {}) => {
    calls.push({ url, headers: init.headers ?? {} });
    const route = routes[new URL(url).pathname];
    if (route instanceof Error) throw route;
    return { ok: route.status === undefined || route.status < 400, status: route.status ?? 200, json: async () => route.body };
  };
  fn.calls = calls;
  return fn;
}

describe('normalizeSymbol', () => {
  it('upper-cases and drops exchange and class suffixes', () => {
    expect(normalizeSymbol('psu-u.to')).toBe('PSU');
    expect(normalizeSymbol('BRK.B')).toBe('BRK');
    expect(normalizeSymbol('nvda')).toBe('NVDA');
    expect(normalizeSymbol(undefined)).toBeNull();
  });
});

describe('loadFilterSymbols', () => {
  const routes = {
    '/api/portfolio': { body: { items: [{ symbol: 'NVDA' }, { symbol: 'PSU-U.TO' }, { symbol: 'USD_CASH' }], dataSource: 'domain_model_sqlite' } },
    '/api/screener/watchlist': { body: [{ ticker: 'AMD' }, { ticker: 'nvda' }] },
  };

  it('merges portfolio and watchlist symbols, de-duplicated', async () => {
    const symbols = await loadFilterSymbols({ baseUrl: 'http://x', token: 't', fetchFn: fakeFetch(routes) });
    expect(symbols.sort()).toEqual(['AMD', 'NVDA', 'PSU', 'USD_CASH'].sort());
  });

  it('sends the local API token as a bearer header on both requests', async () => {
    const f = fakeFetch(routes);
    await loadFilterSymbols({ baseUrl: 'http://x', token: 'secret', fetchFn: f });
    expect(f.calls).toHaveLength(2);
    for (const c of f.calls) expect(c.headers.Authorization).toBe('Bearer secret');
  });

  it('an empty portfolio is an empty list, not an error', async () => {
    const f = fakeFetch({ ...routes, '/api/portfolio': { body: { items: [], dataSource: 'empty' } }, '/api/screener/watchlist': { body: [] } });
    expect(await loadFilterSymbols({ baseUrl: 'http://x', token: 't', fetchFn: f })).toEqual([]);
  });

  it('an unreachable backend is an explicit error naming how to start it', async () => {
    const f = fakeFetch({ '/api/portfolio': new Error('ECONNREFUSED') });
    await expect(loadFilterSymbols({ baseUrl: 'http://x', token: 't', fetchFn: f }))
      .rejects.toThrow(/backend.*not reachable.*run_investment_toolkit\.py/i);
  });

  it('a non-OK response is an explicit error with the status', async () => {
    const f = fakeFetch({ ...routes, '/api/portfolio': { status: 401, body: {} } });
    await expect(loadFilterSymbols({ baseUrl: 'http://x', token: 't', fetchFn: f })).rejects.toThrow(/401/);
  });
});

describe('readApiToken', () => {
  it('prefers LOCAL_API_TOKEN from the environment', () => {
    expect(readApiToken({ LOCAL_API_TOKEN: 'from-env' })).toBe('from-env');
  });
});

describe('cli.js', () => {
  const source = readFileSync(join(here, '..', 'cli.js'), 'utf8');
  it('reads no portfolio file and prints no DEBUG line', () => {
    expect(source).not.toMatch(/portfolio\.json/);
    expect(source).not.toMatch(/watchlist\.json/);
    expect(source).not.toMatch(/DEBUG:/);
  });
});
