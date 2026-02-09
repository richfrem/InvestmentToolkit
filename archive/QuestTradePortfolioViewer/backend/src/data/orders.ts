import type { QuestradeOrder } from '../types/index.ts';

export let orders: QuestradeOrder[] = [];

export const updateOrders = (newOrders: QuestradeOrder[]) => {
  orders = newOrders;
};

export const getOrders = (): QuestradeOrder[] => {
  return orders;
};
