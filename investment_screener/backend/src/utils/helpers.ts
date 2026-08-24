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
 *   - data/domain_model.sqlite via PortfolioRepository.getExchangeRate()
 *     (getLiveUsdCadRate reads the single broker_exchange_rate scalar — Wave 3
 *     Task 8 closed the former portfolio.json dependency; the rate is inferred at
 *     sync time from TV's native CAD/USD totals and stored once, per ADR-030's
 *     Wave 3 addendum and CLAUDE.md pitfall #27)
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
import { PORTFOLIO_FILE, TARGET_PORTFOLIO_FILE, DOMAIN_MODEL_DB_FILE } from './paths';
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
     * Wave 3 Task 8 closed the former portfolio.json dependency here (the CAD gap's
     * TS face; its Python twin is portfolio_repository.py::load_portfolio_state_from_db).
     * Per ADR-030's Wave 3 addendum only the FX rate (a genuine broker fact) is
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

