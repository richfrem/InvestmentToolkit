/**
 * @vitest-environment jsdom
 * Purpose: the Trade Log page orders by trade date, reports executed-trade freshness and offers the refresh command.
 * Layer: Frontend integration. Usage: vitest run tests/TradeLogView.test.tsx.
 * Key Functions: ordering, freshness and command-chip cases.
 * Key Input Dependencies: real helpers and component; TradeLogEntry rows shaped like GET /api/trading/log.
 */
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CopyCommandChip } from '../src/components/CopyCommandChip';
import type { TradeLogEntry } from '../src/services/api';
import {
    TRADE_LOG_PAGE_SIZE, TRADE_SYNC_COMMAND, daysSince, latestFilledTrade, recentFirst, tradeDateParts,
} from '../src/utils/tradeLogView';

afterEach(cleanup);

const entry = (id: string, date: string, status: string, loggedAt = '2026-10-08T13:00:00Z') =>
    ({ id, ticker: id.toUpperCase(), action: 'sell', shares: 1, price: 1, date, status, loggedAt } as TradeLogEntry);

it('orders by trade date, not by when the row was imported', () => {
    // An old cancelled plan logged long ago, and two fills imported in one batch (same loggedAt).
    const rows = [entry('old', '2026-05-18', 'cancelled', '2026-05-18T13:58:00Z'), entry('sep', '2026-09-11', 'filled'), entry('oct', '2026-10-06', 'filled')];
    expect(recentFirst(rows).map(row => row.id)).toEqual(['oct', 'sep', 'old']);
    expect(rows.map(row => row.id)).toEqual(['old', 'sep', 'oct']); // input is not mutated
});

it('reports the newest executed trade and ignores planned or cancelled rows', () => {
    const rows = [entry('plan', '2026-10-07', 'logged'), entry('cancel', '2026-10-08', 'cancelled'), entry('fill', '2026-10-06', 'filled')];
    expect(latestFilledTrade(rows)?.id).toBe('fill');
    expect(latestFilledTrade(rows.slice(0, 2))).toBeNull();
});

it('counts whole calendar days and rejects unusable dates', () => {
    const today = new Date(2026, 9, 8, 23, 30);
    expect(daysSince('2026-10-06', today)).toBe(2);
    expect(daysSince('2026-10-08', today)).toBe(0);
    expect(daysSince('not-a-date', today)).toBeNull();
    expect(daysSince(null, today)).toBeNull();
    expect(TRADE_LOG_PAGE_SIZE).toBe(100);
});

it('copies the refresh command and confirms it', async () => {
    let copied = '';
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: async (text: string) => { copied = text; } }, configurable: true });
    render(<CopyCommandChip command={TRADE_SYNC_COMMAND} label="Refresh trades via" />);
    fireEvent.click(screen.getByRole('button', { name: 'Refresh trades via /questrade-sync-portfolio' }));
    await waitFor(() => expect(screen.getByText('Copied /questrade-sync-portfolio!')).toBeTruthy());
    expect(copied).toBe('/questrade-sync-portfolio');
});

it('shows the trade day and the stored Eastern order time without shifting time zones', () => {
    expect(tradeDateParts('2026-10-06T11:49:05-04:00')).toEqual({ day: '2026-10-06', time: '11:49 AM ET' });
    expect(tradeDateParts('2026-10-06T15:09:05-04:00')).toEqual({ day: '2026-10-06', time: '3:09 PM ET' });
    expect(tradeDateParts('2026-10-06T00:05:00-04:00').time).toBe('12:05 AM ET');
    expect(tradeDateParts('2026-10-06')).toEqual({ day: '2026-10-06', time: null });
    expect(tradeDateParts(null)).toEqual({ day: '—', time: null });
});

it('orders trades on the same day by their time, and counts days from a timestamped date', () => {
    const rows = [entry('early', '2026-10-06T11:15:43-04:00', 'filled'), entry('late', '2026-10-06T11:49:05-04:00', 'filled'), entry('dayonly', '2026-10-06', 'filled')];
    expect(recentFirst(rows).map(row => row.id)).toEqual(['late', 'early', 'dayonly']);
    expect(daysSince('2026-10-06T11:49:05-04:00', new Date(2026, 9, 8))).toBe(2);
});
