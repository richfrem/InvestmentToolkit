import type { QuestradeBalance } from '../types/index.ts';

export let balances: QuestradeBalance[] = [];

export const updateBalances = (newBalances: QuestradeBalance[]) => {
  balances = newBalances;
};

export const getBalances = (): QuestradeBalance[] => {
  return balances;
};
