/**
 * tradeSizing.ts - The share count the Buy and Sell buttons pre-fill.
 *
 * Purpose:
 *     Suggests an order size that would close the gap between a position's actual and target
 *     weight at the current price. It is only a starting number for the trade preparation
 *     dialog: the owner always confirms or edits it, and nothing is placed from here. Missing
 *     inputs give one share rather than a guess.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     suggestedShares({ actualPct: 1, targetPct: 3, price: 30, portfolioValue: 10000 })  // 6
 *
 * Key Functions (Index):
 *     - suggestedShares(): shares to close the weight gap, at least one
 *
 * Key Input Dependencies:
 *     - none (pure)
 *
 * Key Output Dependencies:
 *     - PortfolioPage row actions
 */

export interface SizingInput {
    actualPct: number | null;
    targetPct: number | null;
    price: number | null;
    /** Total portfolio value in the same currency as the price. */
    portfolioValue: number | null;
}

/** Whole shares that close the weight gap at ``price`` (rounded down); one when anything is unknown. */
export function suggestedShares({ actualPct, targetPct, price, portfolioValue }: SizingInput): number {
    if (!actualPct || !targetPct || !price || !portfolioValue || portfolioValue <= 0) return 1;
    const dollarGap = (Math.abs(targetPct - actualPct) * portfolioValue) / 100;
    return Math.max(1, Math.floor(dollarGap / price));
}
