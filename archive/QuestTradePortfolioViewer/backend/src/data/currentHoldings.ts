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