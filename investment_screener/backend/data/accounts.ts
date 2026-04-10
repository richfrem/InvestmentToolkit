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
