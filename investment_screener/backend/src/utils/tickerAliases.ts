/**
 * tickerAliases.ts — Canonical ticker normalization for broker symbols.
 *
 * TypeScript mirror of py_services/ticker_aliases.py — keep the two maps in
 * sync. TradingView/Questrade return broker-format symbols (PSU.U, PSU.U.TO);
 * the canonical thesis symbol is the Yahoo/TSX hyphen form (PSU-U.TO).
 * Every sync path that writes portfolio.json MUST normalize through here,
 * otherwise the PSU duplicate-row bug returns.
 */

export const TICKER_ALIASES: Record<string, string> = {
    'PSU.U': 'PSU-U.TO',
    'PSU.U.TO': 'PSU-U.TO',
};

/** Return the canonical ticker, resolving any broker aliases. */
export function normalizeTicker(ticker: string): string {
    return TICKER_ALIASES[ticker] ?? ticker;
}
