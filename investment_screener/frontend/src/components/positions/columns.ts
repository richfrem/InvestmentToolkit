/**
 * columns.ts - The one column registry for every ticker table in the web app.
 *
 * Purpose:
 *     Each column is defined once here: label, help text, width, how it sorts and which cell
 *     renders it. Screens never declare their own columns; they pick ids from this registry
 *     through a preset (presets.ts). Weight, stance and valuation values all come from the same
 *     shared sources: the position row (database read model), the shared recommendation
 *     (stanceOf, risk_reward) and the privacy setting. Add or change a column here and every
 *     table that uses it changes.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const col = COLUMNS_BY_ID['actualPct'];  col.cell(row, { rec, hidden: false });
 *
 * Key Functions (Index):
 *     - COLUMNS / COLUMNS_BY_ID: the registry
 *
 * Key Input Dependencies:
 *     - cells.tsx, RiskRewardCell, utils/riskReward (RISK_REWARD_COLUMNS, fairValueGap)
 *     - positionMath (formatWeight, formatGap, moneyText)
 *
 * Key Output Dependencies:
 *     - PositionsTable, presets.ts
 */
import { createElement, type ReactNode } from 'react';
import type { RecommendationRecord } from '../../services/api';
import { fmtDollar, fmtPct, fmtPrice, safeNum } from '../../utils/formatters';
import { RISK_REWARD_COLUMNS, fairValueGap, riskRewardRowFields, stanceOf } from '../../utils/riskReward';
import { RiskRewardCell } from '../RiskRewardCell';
import { ActionCell, MonoCell, NameCell, TextCell, TickerCell } from './cells';
import { formatGap, formatWeight, moneyText, type PositionRow, type PositionTotals } from './positionMath';

export interface CellContext {
    rec?: RecommendationRecord | null;
    /** Privacy mode: dollar values are masked. */
    hidden: boolean;
}

export interface PositionColumn {
    id: string;
    label: string;
    title?: string;
    align: 'left' | 'right';
    width: number;
    sort?: (row: PositionRow, rec?: RecommendationRecord | null) => number | string | null;
    cell: (row: PositionRow, ctx: CellContext) => ReactNode;
    total?: (totals: PositionTotals) => ReactNode;
}

const mono = (text: string): ReactNode => createElement(MonoCell, null, text);

const riskRewardColumns: PositionColumn[] = RISK_REWARD_COLUMNS.map(c => ({
    id: c.id, label: c.label, title: c.title, align: c.align, width: c.width,
    sort: (_row, rec) => riskRewardRowFields(rec)[c.id],
    cell: (_row, ctx) => createElement(RiskRewardCell, { columnId: c.id, rec: ctx.rec, hideValues: ctx.hidden }),
}));

const priceOf = (row: PositionRow, rec?: RecommendationRecord | null): number | null =>
    row.currentPrice ?? safeNum(rec?.price);
const fairValueOf = (rec?: RecommendationRecord | null): number | null => safeNum(rec?.fair_value);

export const COLUMNS: PositionColumn[] = [
    { id: 'symbol', label: 'Ticker', align: 'left', width: 80,
      sort: row => row.ticker,
      cell: row => createElement(TickerCell, { row }) },
    { id: 'name', label: 'Name', align: 'left', width: 170,
      sort: row => row.name,
      cell: row => createElement(NameCell, { row }) },
    { id: 'action', label: 'Action', align: 'left', width: 170,
      title: 'The one action every page shows: the valuation action, reconciled with your standing decision.',
      sort: (row, rec) => stanceOf(rec) ?? row.action,
      cell: (row, ctx) => createElement(ActionCell, { row, rec: ctx.rec }) },
    ...riskRewardColumns,
    { id: 'shares', label: 'Shares', align: 'right', width: 70,
      title: 'Shares held across all accounts.',
      sort: row => row.shares,
      cell: row => mono(row.held ? row.shares.toLocaleString(undefined, { maximumFractionDigits: 4 }) : '—') },
    { id: 'actualPct', label: 'Actual %', align: 'right', width: 90,
      title: 'Current weight in the portfolio, from the one weight calculation (live prices, cash included in the total).',
      sort: row => row.actualPct,
      cell: row => mono(formatWeight(row.actualPct)),
      total: t => mono(formatWeight(t.actualPct)) },
    { id: 'targetPct', label: 'Target %', align: 'right', width: 90,
      title: 'Target weight from the thesis. Context only: targets never drive the action.',
      sort: row => row.targetPct,
      cell: row => mono(formatWeight(row.targetPct)),
      total: t => mono(formatWeight(t.targetPct)) },
    { id: 'gapPct', label: 'Gap', align: 'right', width: 80,
      title: 'Actual weight minus target weight, in percentage points.',
      sort: row => row.gapPct,
      cell: row => mono(formatGap(row.gapPct)),
      total: t => mono(formatGap(t.gapPct)) },
    { id: 'fairValue', label: 'Fair Value', align: 'right', width: 95,
      title: 'The saved valuation the action is based on.',
      sort: (_row, rec) => fairValueOf(rec),
      cell: (_row, ctx) => mono(moneyText(fairValueOf(ctx.rec), ctx.hidden, fmtDollar)) },
    { id: 'price', label: 'Price', align: 'right', width: 90,
      sort: (row, rec) => priceOf(row, rec),
      cell: (row, ctx) => mono(moneyText(priceOf(row, ctx.rec), false, fmtPrice)) },
    { id: 'upside', label: 'Upside', align: 'right', width: 85,
      title: 'Fair value above (+) or below (−) the current price.',
      sort: (row, rec) => fairValueGap(fairValueOf(rec), priceOf(row, rec)).upside,
      cell: (row, ctx) => mono(fmtPct(fairValueGap(fairValueOf(ctx.rec), priceOf(row, ctx.rec)).upside)) },
    { id: 'marketValue', label: 'Mkt Value', align: 'right', width: 95,
      sort: row => row.marketValue,
      cell: (row, ctx) => mono(moneyText(row.marketValue, ctx.hidden, fmtDollar)) },
    { id: 'bookValue', label: 'Book Value', align: 'right', width: 95,
      sort: row => row.bookValue,
      cell: (row, ctx) => mono(moneyText(row.bookValue, ctx.hidden, fmtDollar)) },
    { id: 'averageCost', label: 'Avg Cost', align: 'right', width: 85,
      sort: row => row.averageCost,
      cell: (row, ctx) => mono(moneyText(row.averageCost, ctx.hidden, fmtPrice)) },
    { id: 'subStrategyId', label: 'Strategy', align: 'left', width: 140,
      sort: row => row.subStrategyId,
      cell: row => createElement(TextCell, null, row.subStrategyId) },
];

export const COLUMNS_BY_ID: Record<string, PositionColumn> = Object.fromEntries(COLUMNS.map(c => [c.id, c]));
