/**
 * @vitest-environment jsdom
 * Purpose: the recent-trade tag shows filled trades beside the action and nothing when there are none.
 * Layer: Frontend integration. Usage: vitest run tests/RecentTradeTag.test.tsx.
 * Key Functions: acted, opposed and empty cases.
 * Key Input Dependencies: real component; RecommendationRecord shaped like recent_trades.py output.
 */
import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { RecentTradeTag } from '../src/components/RecentTradeTag';
import type { RecommendationRecord } from '../src/services/api';

afterEach(cleanup);

const record = (recent_trades: RecommendationRecord['recent_trades']) =>
    ({ ticker: 'ZS', action: 'TRIM', recent_trades } as RecommendationRecord);
const last = { date: '2026-10-06', action: 'sell', shares: 1, price: 210.36, account: 'RRSP' };

it('shows a trim that was already acted on, with the full note on hover', () => {
    render(<RecentTradeTag rec={record({ window_days: 14, sold_shares: 3, bought_shares: 0, count: 2, last,
        context: { status: 'ACTED', note: 'Sold 3 shares in the last 14 days, last on 2026-10-06: TRIM already acted on' } })} />);
    const tag = screen.getByText(/Sold 3 · Oct 6/);
    expect(tag.className).toContain('text-emerald-300');
    expect(tag.getAttribute('title')).toContain('TRIM already acted on');
});

it('calls out a trade that runs against the action', () => {
    render(<RecentTradeTag rec={record({ window_days: 14, sold_shares: 0, bought_shares: 2.5, count: 1,
        last: { ...last, action: 'buy', shares: 2.5 }, context: { status: 'OPPOSED', note: 'Bought 2.5 shares, while the action is TRIM' } })} />);
    expect(screen.getByText(/Bought 2.5 · Oct 6/).className).toContain('text-amber-300');
});

it('renders nothing without recent filled trades or on older backends', () => {
    const empty = render(<RecentTradeTag rec={record({ window_days: 14, sold_shares: 0, bought_shares: 0, count: 0, last: null,
        context: { status: 'NONE', note: '' } })} />);
    expect(empty.container.textContent).toBe('');
    cleanup();
    expect(render(<RecentTradeTag rec={record(undefined)} />).container.textContent).toBe('');
});
