/**
 * positions.ts (TypeScript Data Store)
 * =====================================
 *
 * Purpose:
 *     In-memory singleton store for raw Questrade brokerage positions.
 *     Stores the primary list of tickers, share counts, and market prices as reported by the brokerage.
 *
 * Layer: Backend / Data / State Management
 *
 * Usage Examples:
 *     import { getPositions, updatePositions } from '../data/positions';
 *     const rawPositions = getPositions();
 *
 * Key Functions:
 *     - updatePositions() - Synchronizes the raw position list after a Questrade API fetch
 *     - getPositions() - Returns the currently held brokerage positions
 */
import type { QuestradePosition } from '../types/index.ts';

export let positions: QuestradePosition[] = [];

export const updatePositions = (newPositions: QuestradePosition[]) => {
  positions = newPositions;
};

export const getPositions = (): QuestradePosition[] => {
  return positions;
};
