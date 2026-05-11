/**
 * balances.ts (TypeScript Data Store)
 * =====================================
 *
 * Purpose:
 *     In-memory singleton store for Questrade account balances.
 *     Maintains real-time visibility into CAD/USD cash, buying power, and total equity.
 *
 * Layer: Backend / Data / State Management
 *
 * Usage Examples:
 *     import { getBalances, updateBalances } from '../data/balances';
 *     const totals = getBalances();
 *
 * Key Functions:
 *     - updateBalances() - Persists fresh balance data fetched from the Questrade Data Engine
 *     - getBalances() - Returns the currently cached balance collection
 */
import type { QuestradeBalance } from '../types/index.ts';

export let balances: QuestradeBalance[] = [];

export const updateBalances = (newBalances: QuestradeBalance[]) => {
  balances = newBalances;
};

export const getBalances = (): QuestradeBalance[] => {
  return balances;
};
