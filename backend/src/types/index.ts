// Questrade Order schema (aligned with Questrade API /accounts/:id/orders response)
export interface QuestradeOrderLeg {
  // Add properties as needed for multi-leg orders
}

export interface QuestradeOrder {
  id: number;
  symbol: string;
  symbolId: number;
  totalQuantity: number;
  openQuantity: number;
  filledQuantity: number;
  canceledQuantity: number;
  side: string;
  orderType: string;
  limitPrice?: number;
  stopPrice?: number;
  isAllOrNone: boolean;
  isAnonymous: boolean;
  icebergQuantity?: number;
  minQuantity?: number;
  avgExecPrice?: number;
  lastExecPrice?: number;
  source?: string;
  timeInForce?: string;
  gtdDate?: string;
  state: string;
  clientReasonStr?: string;
  chainId?: number;
  creationTime?: string;
  updateTime?: string;
  notes?: string;
  primaryRoute?: string;
  secondaryRoute?: string;
  orderRoute?: string;
  venueHoldingOrder?: string;
  commissionCharged?: number;
  exchangeOrderId?: string;
  isSignificantShareholder?: boolean;
  isInsider?: boolean;
  isLimitOffsetInDollar?: boolean;
  userId?: number;
  placementCommission?: number;
  legs?: QuestradeOrderLeg[];
  strategyType?: string;
  triggerStopPrice?: number;
  orderGroupId?: number;
  orderClass?: string;
  mainChainId?: number;
}

export interface QuestradeOrdersResponse {
  orders: QuestradeOrder[];
}
// Questrade Balance schema (aligned with Questrade API /accounts/:id/balances response)
export interface QuestradeBalance {
  currency: string; // e.g., "USD", "CAD"
  cash: number;
  marketValue: number;
  totalEquity: number;
  buyingPower: number;
  maintenanceExcess: number;
  isRealTime: boolean;
}

export interface QuestradeBalancesResponse {
  perCurrencyBalances: QuestradeBalance[];
  combinedBalances: QuestradeBalance[];
  sodPerCurrencyBalances: QuestradeBalance[];
  sodCombinedBalances: QuestradeBalance[];
}
// Questrade Position schema (aligned with Questrade API /accounts/:id/positions response)
export interface QuestradePosition {
  symbol: string;
  symbolId: number;
  openQuantity: number;
  closedQuantity: number;
  currentMarketValue: number;
  currentPrice: number;
  averageEntryPrice: number;
  closedPnl: number;
  openPnl: number;
  totalCost: number;
  isRealTime: boolean;
  isUnderReorg: boolean;
}

export interface QuestradePositionsResponse {
  positions: QuestradePosition[];
}
// Questrade Account schema (aligned with Questrade API /accounts response)
export interface QuestradeAccount {
  type: string; // e.g., "Cash", "Margin"
  number: string; // Eight-digit account number
  status: string; // e.g., "Active"
  isPrimary: boolean;
  isBilling: boolean;
  clientAccountType: string; // e.g., "Individual"
  userId: number;
}

export interface QuestradeAccountsResponse {
  accounts: QuestradeAccount[];
}
import { z } from 'zod';

export const HoldingSchema = z.object({
  symbol: z.string(),
  quantity: z.number(),
  bookValue: z.number(),
  marketValue: z.number(),
});

export type Holding = z.infer<typeof HoldingSchema>;

export interface QuestradeAuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
