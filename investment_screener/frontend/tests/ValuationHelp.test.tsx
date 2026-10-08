/**
 * @vitest-environment jsdom
 * Purpose: verify financial terms open the shared valuation explanations.
 * Layer: Frontend integration. Usage: vitest run tests/ValuationHelp.test.tsx.
 * Key Functions: term popup interaction and acronym-boundary checks.
 * Key Input Dependencies: real SmartText and HelpModalProvider components.
 */
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { HelpModalProvider } from '../src/components/HelpModal';
import { SmartText } from '../src/components/SmartText';

afterEach(cleanup);

it.each([
    ['DCF', 'DCF (Discounted Cash Flow)', /capital spending and working capital/],
    ['WACC', 'WACC (Weighted Average Cost of Capital)', /cash flows before financing payments/],
    ['Cost of Equity', 'Cost of Equity', /future EPS.*exit P\/E/],
])('opens the shared explanation for %s', (term, title, explanation) => {
    render(<HelpModalProvider><SmartText text={`This model uses ${term}.`} /></HelpModalProvider>);
    fireEvent.click(screen.getByRole('button', { name: term }));
    expect(screen.getByRole('heading', { name: title })).toBeTruthy();
    expect(screen.getByText(explanation)).toBeTruthy();
});

it('does not turn part of a ticker or other word into a DCF help button', () => {
    render(<HelpModalProvider><SmartText text="DCF, DCFX, WACC." /></HelpModalProvider>);
    expect(screen.getAllByRole('button', { name: 'DCF' })).toHaveLength(1);
    expect(screen.getByText(/DCFX/)).toBeTruthy();
});
