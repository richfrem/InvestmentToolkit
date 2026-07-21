/**
 * helpers.ts - Express backend utility helper routines.
 * 
 * Purpose:
 *   Aggregates general helper functionality including exchange rates retrieval,
 *   TradingView TCP connectivity checks, ticker format validation, and Python bridge execution.
 * 
 * Key Input Dependencies:
 *   - ./paths (for portfolio JSON paths references)
 *   - ../services/bridge (for spawning Python analytical scripts)
 *   - investment_screener/backend/data/portfolio.json (getLiveUsdCadRate reads
 *     tvSnapshot broker balance totals for FX inference — Wave 3 Task 6
 *     investigation found no SQLite equivalent table exists yet for
 *     per-currency broker balances; NOT rewired, documented stop, see the
 *     comment inside getLiveUsdCadRate)
 * 
 * Key Output Dependencies:
 *   None
 * 
 * Functions Index:
 *   - isValidTicker(ticker: string) - Validate that a ticker symbol conforms to standard format
 *   - getLiveUsdCadRate(fallback: number) - Retrieve the current USD to CAD exchange conversion rate
 *   - isTradingViewConnected(tvPort: number) - Check if the TradingView CDP remote debugging port is open
 *   - getPythonActions() - Query portfolio actions and recommendation targets computed by the Python backend
 */

import net from 'net';
import { PORTFOLIO_FILE, TARGET_PORTFOLIO_FILE } from './paths';
import { spawnPythonScript } from '../services/bridge';

/**
 * Validate that a ticker symbol conforms to standard alphanumeric structure.
 * 
 * @param {string} ticker - Target symbol to validate
 * @returns {boolean} True if symbol conforms to the character criteria
 */
export const isValidTicker = (ticker: string): boolean => {
    /**
     * Matches string characters against a strict 1-10 length uppercase and punctuation regular expression.
     */
    return /^[A-Z0-9.\-_]{1,10}$/.test(ticker);
};

/**
 * Retrieve the current USD to CAD exchange conversion rate.
 * 
 * @param {number} fallback - Default rate level to use on fetch failures
 * @returns {Promise<number>} Current conversion rate multiplier
 */
export async function getLiveUsdCadRate(fallback: number): Promise<number> {
    /**
     * Attempts to infer the live exchange rate directly from the TV snapshot in portfolio.json first.
     * Otherwise, falls back to the EXCHANGE_RATE_API_KEY pair endpoint or a static fallback rate.
     *
     * Wave 3 Task 6 investigation (NOT rewired — documented stop, not an oversight):
     * this reads `tvSnapshot.snapshots[].balances.totalEquityCADCombined/USDCombined`
     * from portfolio.json. No table in domain_model.sqlite stores per-currency broker
     * account balance totals (only per-position quantity/price via account_investment/
     * investment_price) — this is the exact same documented gap as
     * py_services/domain_model/portfolio_repository.py::load_portfolio_state_from_db's
     * `exchange_rate` field (see that function's comment). Inventing a new table for
     * this single call site is out of scope (no schema changes permitted this wave);
     * routes/stock.ts and routes/portfolio.ts both still call this function unchanged
     * for exchangeRate even after their own totalUSD/totalCAD reads were rewired onto
     * SQLite in this same task.
     */
    try {
        const fs = require('fs');
        if (fs.existsSync(PORTFOLIO_FILE)) {
            const data = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
            const snapshots = data?.tvSnapshot?.snapshots || [];
            let totalCAD = 0;
            let totalUSD = 0;
            for (const snap of snapshots) {
                const b = snap?.balances;
                if (b) {
                    const cad = b.totalEquityCADCombined ?? b.totalEquityCAD ?? 0;
                    const usd = b.totalEquityUSDCombined ?? b.totalEquityUSD ?? 0;
                    totalCAD += cad;
                    totalUSD += usd;
                }
            }
            if (totalUSD > 0 && totalCAD > 0) {
                const inferredRate = totalCAD / totalUSD;
                console.log(`[ExchangeRate] Inferred live rate from TV balances: ${inferredRate.toFixed(4)}`);
                return inferredRate;
            }
        }
    } catch (e: any) {
        console.warn(`[ExchangeRate] Failed to infer rate from TV snapshot:`, e.message);
    }

    return fallback;
}

/**
 * Check if the TradingView CDP remote debugging port is open.
 * 
 * @param {number} tvPort - TCP port to connect to
 * @returns {Promise<boolean>} True if the TCP port accepts connections
 */
export function isTradingViewConnected(tvPort = parseInt(process.env.TV_CDP_PORT || '9222', 10)): Promise<boolean> {
    /**
     * Instantiates a net.Socket, attempts to connect to localhost:tvPort with 300ms timeout,
     * and resolves true on successful connection.
     */
    return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(300);
        socket.on('connect', () => { socket.destroy(); resolve(true); });
        socket.on('timeout', () => { socket.destroy(); resolve(false); });
        socket.on('error', () => resolve(false));
        socket.connect(tvPort, 'localhost');
    });
}

/**
 * Query portfolio actions and recommendation targets computed by the Python backend.
 * 
 * @returns {Promise<Record<string, string>>} Action mappings computed per ticker symbol
 */
export async function getPythonActions(): Promise<Record<string, string>> {
    /**
     * Spawns portfolio_action.py via the bridge, passing portfolio and target file parameters,
     * returning the mapped actions dictionary.
     */
    try {
        const data = await spawnPythonScript('portfolio_action.py', [
            '--all',
            '--portfolio', PORTFOLIO_FILE,
            '--target', TARGET_PORTFOLIO_FILE
        ]);
        return data || {};
    } catch (err) {
        console.error('[Actions] Failed to fetch python actions:', err);
        return {};
    }
}

