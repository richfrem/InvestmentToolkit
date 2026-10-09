/**
 * alert_filter.js - Symbol list for `alert list --filter`.
 *
 * Purpose:
 *   Alerts are filtered to the symbols you hold or watch. Holdings and the watchlist are read
 *   from the Express backend's SQLite-backed endpoints (Node cannot import the Python
 *   domain_model package, and the repositories are the only code that touches the database).
 *   Requests carry the backend's local API token. An unreachable or failing backend is an
 *   explicit error; an empty portfolio is an empty list.
 *
 * Key Functions (Index):
 *   - normalizeSymbol(symbol): upper-cased root symbol without exchange or class suffix
 *   - readApiToken(env, repoRoot): LOCAL_API_TOKEN, else .runtime/api-token
 *   - loadFilterSymbols({ baseUrl, token, fetchFn }): unique symbols from portfolio + watchlist
 *
 * Key Input Dependencies:
 *   - GET <baseUrl>/api/portfolio ({ items: [{ symbol }] }) and GET <baseUrl>/api/screener/watchlist
 *   - .runtime/api-token at the repository root (or LOCAL_API_TOKEN)
 *
 * Key Output Dependencies:
 *   - None
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const DEFAULT_BASE_URL = 'http://localhost:3001';

/** Root symbol: `PSU-U.TO` -> `PSU`, `brk.b` -> `BRK`; null for a missing symbol. */
export function normalizeSymbol(symbol) {
  return symbol ? symbol.split('.')[0].split('-')[0].toUpperCase() : null;
}

/** The backend's local API token: LOCAL_API_TOKEN, else the repo's .runtime/api-token (null if neither). */
export function readApiToken(env = process.env, repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..', '..')) {
  if (env.LOCAL_API_TOKEN) return env.LOCAL_API_TOKEN;
  try {
    return readFileSync(join(repoRoot, '.runtime', 'api-token'), 'utf8').trim();
  } catch {
    return null;
  }
}

async function getJson(fetchFn, url, token, what) {
  let resp;
  try {
    resp = await fetchFn(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  } catch (err) {
    throw new Error(`Cannot load ${what}: the backend is not reachable at ${url} (${err.message}). Start the app with python3 run_investment_toolkit.py.`);
  }
  if (!resp.ok) throw new Error(`Cannot load ${what}: ${url} returned HTTP ${resp.status}.`);
  return resp.json();
}

/** Unique, normalized symbols from the stored portfolio and the watchlist. */
export async function loadFilterSymbols({ baseUrl = DEFAULT_BASE_URL, token = readApiToken(), fetchFn = fetch } = {}) {
  const portfolio = await getJson(fetchFn, `${baseUrl}/api/portfolio`, token, 'the portfolio');
  const watchlist = await getJson(fetchFn, `${baseUrl}/api/screener/watchlist`, token, 'the watchlist');
  const rows = [...(portfolio.items ?? []), ...(watchlist ?? [])];
  return [...new Set(rows.map(r => normalizeSymbol(r.symbol || r.ticker)).filter(Boolean))];
}
