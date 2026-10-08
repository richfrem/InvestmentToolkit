/**
 * @vitest-environment jsdom
 * Purpose: ensure the thesis modal displays persisted scenario values without revaluing them.
 * Layer: Frontend regression tests. Key Functions: saved and absent target assertions.
 * Key Input Dependencies: AIAnalysisModal, saved Projection contract, React and jsdom.
 */
import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { AIAnalysisModal } from '../src/components/AIAnalysisModal';
import { HelpModalProvider } from '../src/components/HelpModal';
import type { Projection } from '../src/services/api';

afterEach(cleanup);

const projection = {
    ticker: 'APLD', id: 'saved-apld', source: 'AI_AGENT', version: 11,
    savedAt: '2026-10-07', snapshot: { price: 25.34, revenue: 0, shares: 302387140 },
    globalSettings: { discountRate: 12.77, timeHorizon: 5 },
    aiThesis: { action: 'MAINTAIN', fairValue: 27.67, rationale: 'Saved projection', analyzedAt: '2026-10-07' },
    scenarios: {
        bear: { weight: 0.2, growthRate: 24, netMargin: 8, exitPE: 15, scenarioPrice: 2.75 },
        base: { weight: 0.52, growthRate: 35, netMargin: 18, exitPE: 28, scenarioPrice: 21.09 },
        bull: { weight: 0.28, growthRate: 45, netMargin: 25, exitPE: 35, scenarioPrice: 57.7 },
    },
} as unknown as Projection;

it('shows persisted targets even when earnings inputs cannot reproduce them', () => {
    render(<HelpModalProvider><AIAnalysisModal symbol="APLD" isOpen onClose={() => {}} initialProjection={projection} /></HelpModalProvider>);
    for (const target of ['$2.75', '$21.09', '$57.70']) expect(screen.getByText(target)).toBeTruthy();
    expect(screen.getByText('Discount Rate: 12.77%')).toBeTruthy();
});

it('distinguishes an unavailable target from a genuine zero equity value', () => {
    const missing = { ...projection, scenarios: { ...projection.scenarios,
        bear: { ...projection.scenarios.bear, scenarioPrice: 0 },
        base: { ...projection.scenarios.base, scenarioPrice: undefined },
    } };
    render(<HelpModalProvider><AIAnalysisModal symbol="APLD" isOpen onClose={() => {}} initialProjection={missing} /></HelpModalProvider>);
    const rows = screen.getAllByRole('row');
    expect(within(rows[1]).getByText('$0.00')).toBeTruthy();
    expect(within(rows[2]).getAllByText('—')).toHaveLength(2);
});

it('shows an unavailable saved rate without substituting a default', () => {
    const missing = { ...projection, globalSettings: { timeHorizon: 5 } } as Projection;
    render(<HelpModalProvider><AIAnalysisModal symbol="APLD" isOpen onClose={() => {}} initialProjection={missing} /></HelpModalProvider>);
    expect(screen.getByText('Discount Rate: —')).toBeTruthy();
});

it('explains the saved discount rate without closing the thesis', () => {
    render(<HelpModalProvider><AIAnalysisModal symbol="APLD" isOpen onClose={() => {}} initialProjection={projection} /></HelpModalProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Explain Discount Rate (Required Return)' }));
    expect(screen.getByRole('heading', { name: 'Discount Rate (Required Return)' })).toBeTruthy();
    expect(screen.getByText('AI Investment Thesis')).toBeTruthy();
});
