/**
 * accounts.ts (TypeScript Data Store)
 * =====================================
 *
 * Purpose:
 *     In-memory singleton store for Questrade account metadata.
 *     Provides synchronized access to account identifiers, types, and statuses across the backend.
 *
 * Layer: Backend / Data / State Management
 *
 * Usage Examples:
 *     import { getAccounts, updateAccounts } from '../data/accounts';
 *     const current = getAccounts();
 *
 * Key Functions:
 *     - updateAccounts() - Mutates the in-memory account list (invoked by QuestradeSyncService)
 *     - getAccounts() - Thread-safe retrieval of the current account collection
 */
import type { QuestradeAccount } from '../types/index.ts';

export let accounts: QuestradeAccount[] = [];

// Function to update accounts (called on fetch)
export const updateAccounts = (newAccounts: QuestradeAccount[]) => {
  accounts = newAccounts;
};

// Function to get current accounts
export const getAccounts = (): QuestradeAccount[] => {
  return accounts;
};
