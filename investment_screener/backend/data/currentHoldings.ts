/**
 * currentHoldings.ts (TypeScript Data Store)
 * =====================================
 *
 * Purpose:
 *     In-memory singleton store for the consolidated portfolio holdings.
 *     Stores enriched holding data including book prices, current market values, and sector classifications.
 *
 * Layer: Backend / Data / State Management
 *
 * Usage Examples:
 *     import { getCurrentHoldings, updateCurrentHoldings } from '../data/currentHoldings';
 *     const portfolio = getCurrentHoldings();
 *
 * Key Functions:
 *     - updateCurrentHoldings() - Refreshes the active holding list after a successful Questrade/yfinance sync
 *     - getCurrentHoldings() - Provides read access to the enriched portfolio state
 */
import type { Holding } from '../types/index.ts';

export let currentHoldings: Holding[] = [];

// Function to update holdings (called on fetch)
export const updateCurrentHoldings = (holdings: Holding[]) => {
  currentHoldings = holdings;
};

// Function to get current holdings
export const getCurrentHoldings = (): Holding[] => {
  return currentHoldings;
};