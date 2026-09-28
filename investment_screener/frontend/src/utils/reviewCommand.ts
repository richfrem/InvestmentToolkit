/**
 * reviewCommand.ts
 * =====================================
 * Purpose: single source for the slash command the "New Review" buttons copy.
 * The update-stock-analysis skill replaced /guide-valuation on 2026-08-28.
 *
 * Key Functions (Index):
 *   - newReviewCommand(ticker) - returns "/update-stock-analysis {ticker}"
 */

export const REVIEW_COMMAND = '/update-stock-analysis';

export const newReviewCommand = (ticker: string): string => `${REVIEW_COMMAND} ${ticker}`;
