/**
 * helpers.ts - Express backend utility helper routines.
 * 
 * Purpose:
 *   Aggregates general helper functionality including exchange rates retrieval,
 *   TradingView TCP connectivity checks, ticker format validation, and Python bridge execution.
 * 
 * Key Input Dependencies:
 *   - ./paths (data folder and database path constants)
 *   - ../services/bridge (for spawning Python analytical scripts)
 *   - data/domain_model.sqlite via PortfolioRepository.getExchangeRate()
 *     (getLiveUsdCadRate reads the single broker_exchange_rate scalar; the rate
 *     is inferred at sync time from TV's native CAD/USD totals and stored once, per
 *     ADR-030's addendum and AGENTS.md pitfall #27)
 * 
 * Key Output Dependencies:
 *   None
 * 
 * Functions Index:
 *   - isValidTicker(ticker: string) - Validate that a ticker symbol conforms to standard format
 *   - getLiveUsdCadRate(fallback: number) - Retrieve the current USD to CAD exchange conversion rate
 *   - isTradingViewConnected(tvPort: number) - Check if the TradingView CDP remote debugging port is open
 *   - getRecommendations() - Canonical per-ticker recommendations (action + reason) from recommendation.py
 */

import net from 'net';
import { DOMAIN_MODEL_DB_FILE } from './paths';
import { spawnPythonScript } from '../services/bridge';
import { PortfolioRepository } from '../services/PortfolioRepository';

/**
 * Validate that a ticker symbol conforms to standard alphanumeric structure.
 * 
 * @param {string} ticker - Target symbol to validate
 * @returns {boolean} True if symbol conforms to the character criteria
 */
export const isValidTicker = (ticker: string): boolean => {
    /**
     * Matches string characters against a 1-10 length alphanumeric and punctuation regular expression (case-insensitive).
     */
    return /^[A-Za-z0-9.\-_]{1,10}$/.test(ticker);
};

/**
 * Retrieve the current USD to CAD exchange conversion rate.
 * 
 * @param {number} fallback - Default rate level to use on fetch failures
 * @returns {Promise<number>} Current conversion rate multiplier
 */
export async function getLiveUsdCadRate(fallback: number, dbPath: string = DOMAIN_MODEL_DB_FILE): Promise<number> {
    /**
     * Reads the single broker-reported USD->CAD rate from the broker_exchange_rate
     * table (via PortfolioRepository.getExchangeRate()). That scalar was inferred at
     * sync time from TradingView's own native totalEquityCADCombined/USDCombined
     * ratio (CLAUDE.md pitfall #27, never an external FX API) by the sync writer
     * (BrokerSyncService.persistSnapshotToDb / fetch_broker_data._persist_snapshot_to_db).
     *
     * Its Python twin is portfolio_repository.py::load_portfolio_state_from_db.
     * Per ADR-030's addendum only the FX rate (a genuine broker fact) is
     * stored; CAD totals are computed as usd*rate at read time. Falls back to the
     * static `fallback` for a fresh/never-synced DB, matching every other reader's
     * fallback convention.
     */
    let repo: PortfolioRepository | null = null;
    try {
        repo = new PortfolioRepository(dbPath);
        const rate = repo.getExchangeRate();
        if (rate !== null && rate > 0) {
            return rate;
        }
    } catch (e: any) {
        console.warn(`[ExchangeRate] Failed to read rate from domain_model.sqlite:`, e.message);
    } finally {
        if (repo) {
            try { repo.close(); } catch { /* already closed */ }
        }
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
 * Query canonical per-ticker recommendations computed by recommendation.py.
 *
 * @returns {Promise<Record<string, any>>} Records keyed by ticker (action, reason, valuation, upside_pct, held, current_weight_pct)
 */
export async function getRecommendations(dbPath: string = DOMAIN_MODEL_DB_FILE): Promise<Record<string, any>> {
    /**
     * Spawns recommendation.py (the canonical recommendation function) and returns
     * per-ticker records: action, reason, valuation, upside_pct, held, current_weight_pct.
     */
    const records = await spawnPythonScript('recommendation.py', ['--all', '--db', dbPath]);
    if (!records || records.stale) throw new Error('Current recommendations unavailable');
    return records;
}
