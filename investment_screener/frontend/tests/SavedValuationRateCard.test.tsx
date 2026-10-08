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

it('explains an audited cost of equity with its saved inputs and written reason', () => {
    const projection = { ...saved, globalSettings: { discountRate: 12.75, timeHorizon: 5 }, analyticsLog: { valuationModel: { method: 'terminal_earnings',
        discountRateAudit: { rateType: 'COST_OF_EQUITY', selectedRate: 0.127529786, asOf: '2026-10-07', readiness: 'REVIEW_REQUIRED',
            components: { costOfEquity: 0.127529786 },
            inputs: { riskFreeRate: 0.0515, beta: 1.810233, erp: 0.042, rationale: 'Peer beta preferred because the business changed inside every regression window.' } },
    } } } as Projection;
    render(<HelpModalProvider><SavedValuationRateCard projection={projection} /></HelpModalProvider>);
    const why = screen.getByRole('group', { name: 'Why this rate' });
    expect(within(why).getByText('5.15% risk-free + 1.81 beta × 4.2% equity risk premium = 12.75%')).toBeTruthy();
    expect(within(why).getByText('Peer beta preferred because the business changed inside every regression window.')).toBeTruthy();
});

it('explains an audited WACC from its saved capital weights', () => {
    const projection = { ...saved, globalSettings: { discountRate: 8.8, timeHorizon: 5 }, analyticsLog: { valuationModel: { method: 'annual_fcff',
        discountRateAudit: { rateType: 'WACC', selectedRate: 0.088, asOf: '2026-10-07', readiness: 'REVIEW_REQUIRED',
            components: { costOfEquity: 0.10, equityWeight: 0.8, debtWeight: 0.2, costOfDebtAfterTax: 0.04, rawWacc: 0.088 },
            inputs: { riskFreeRate: 0.04, beta: 1, erp: 0.06, rationale: 'Firm cash flows are discounted at the blended cost of capital.' } },
    } } } as Projection;
    render(<HelpModalProvider><SavedValuationRateCard projection={projection} /></HelpModalProvider>);
    const why = screen.getByRole('group', { name: 'Why this rate' });
    expect(within(why).getByText('80% equity × 10% + 20% debt × 4% after tax = 8.8%')).toBeTruthy();
    expect(within(why).getByText('Firm cash flows are discounted at the blended cost of capital.')).toBeTruthy();
});

it('does not invent an explanation for an unaudited rate', () => {
    render(<HelpModalProvider><SavedValuationRateCard projection={saved} /></HelpModalProvider>);
    expect(screen.queryByRole('group', { name: 'Why this rate' })).toBeNull();
});

it('shows unavailable when there is no saved valuation, without inventing 10%', () => {
    render(<HelpModalProvider><SavedValuationRateCard /></HelpModalProvider>);
    expect(screen.getByText('No saved valuation rate')).toBeTruthy();
    expect(screen.queryByText('10.00%')).toBeNull();
});
