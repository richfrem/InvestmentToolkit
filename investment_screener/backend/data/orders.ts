/**
 * orders.ts (TypeScript Data Store)
 * =====================================
 *
 * Purpose:
 *     In-memory singleton store for Questrade trade orders.
 *     Tracks open, filled, and cancelled orders for inclusion in the portfolio activity view.
 *
 * Layer: Backend / Data / State Management
 *
 * Usage Examples:
 *     import { getOrders, updateOrders } from '../data/orders';
 *     const activeTrades = getOrders();
 *
 * Key Functions:
 *     - updateOrders() - Updates the list of active/recent orders from the Questrade sync engine
 *     - getOrders() - Returns the current snapshot of order activity
 */
import type { QuestradeOrder } from '../types/index.ts';

export let orders: QuestradeOrder[] = [];

export const updateOrders = (newOrders: QuestradeOrder[]) => {
  orders = newOrders;
};

export const getOrders = (): QuestradeOrder[] => {
  return orders;
};
