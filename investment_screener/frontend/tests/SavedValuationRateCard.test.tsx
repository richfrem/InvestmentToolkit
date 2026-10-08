/**
 * @vitest-environment jsdom
 * Purpose: saved valuation rate cards display stored values and evidence limits.
 * Layer: Frontend integration. Usage: vitest run tests/SavedValuationRateCard.test.tsx.
 * Key Functions: audited, inherited, and missing-rate interaction tests.
 * Key Input Dependencies: real card, HelpModalProvider, saved API Projection.
 */
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { SavedValuationRateCard } from '../src/components/SavedValuationRateCard';
import { HelpModalProvider } from '../src/components/HelpModal';
import type { Projection } from '../src/services/api';

afterEach(cleanup);
const saved = {
    globalSettings: { discountRate: 12.77, timeHorizon: 5 },
    aiThesis: { fairValue: 27.67 },
} as Projection;

it('shows the inherited saved rate without claiming a verified WACC basis', () => {
    render(<HelpModalProvider><SavedValuationRateCard projection={saved} /></HelpModalProvider>);
    expect(screen.getByText('12.77%')).toBeTruthy();
    expect(screen.getByText('Rate basis unverified')).toBeTruthy();
    expect(screen.queryByText('WACC')).toBeNull();
    expect(screen.getByText('$27.67')).toBeTruthy();
});

it.each([
    ['annual_fcff', 'WACC', 'WACC (Weighted Average Cost of Capital)'],
    ['terminal_earnings', 'COST_OF_EQUITY', 'Cost of Equity'],
])('shows %s rate basis and opens its explanation', (method, rateType, title) => {
    const projection = { ...saved, analyticsLog: { valuationModel: { method,
        discountRateAudit: { rateType, selectedRate: 0.1277, asOf: '2026-10-07', readiness: 'REVIEW_REQUIRED' },
    } } } as Projection;
    render(<HelpModalProvider><SavedValuationRateCard projection={projection} /></HelpModalProvider>);
    expect(screen.getByText('12.77%')).toBeTruthy();
    expect(screen.getByText('Input audit saved; evidence review required')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: `Explain ${title}` }));
    expect(within(screen.getByRole('dialog', { name: title })).getByRole('heading', { name: title })).toBeTruthy();
});

it('shows unavailable when there is no saved valuation, without inventing 10%', () => {
    render(<HelpModalProvider><SavedValuationRateCard /></HelpModalProvider>);
    expect(screen.getByText('No saved valuation rate')).toBeTruthy();
    expect(screen.queryByText('10.00%')).toBeNull();
});
