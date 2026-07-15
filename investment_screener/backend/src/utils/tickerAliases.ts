/**
 * tickerAliases.ts - Canonical ticker symbol normalization.
 * 
 * Purpose:
 *   Normalizes broker-format symbols (e.g. PSU.U.TO) to canonical Yahoo Finance/TSX formats
 *   (e.g. PSU-U.TO) to prevent duplicate holdings rows. Keep in sync with py_services/ticker_aliases.py.
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 * 
 * Functions Index:
 *   - normalizeTicker(ticker: string) - Return the canonical ticker resolving broker aliases
 */

export const TICKER_ALIASES: Record<string, string> = {
    'PSU.U': 'PSU-U.TO',
    'PSU.U.TO': 'PSU-U.TO',
};

/**
 * Return the canonical ticker, resolving any broker aliases.
 * 
 * @param {string} ticker - Broker symbol ticker string
 * @returns {string} Canonical resolved ticker string
 */
export function normalizeTicker(ticker: string): string {
    /**
     * Looks up ticker in aliases hash map and returns the mapped canonical name or the input string on fallback.
     */
    return TICKER_ALIASES[ticker] ?? ticker;
}

