/**
 * Purpose: display saved valuation rates consistently without estimating rates in the browser.
 * Layer: Frontend / Presentation. Usage: savedValuationRate(projection).
 * Key Functions: savedValuationRate — stored percentage, label, help topic, audit limits and saved "why this rate" text.
 * Key Input Dependencies: backend Projection percentage-rate and persisted audit contract.
 */
import type { Projection } from '../services/api';

const pct = (value: unknown) => typeof value === 'number' && Number.isFinite(value)
    ? `${Number((value * 100).toFixed(2))}%` : null;
const record = (value: unknown) => (value && typeof value === 'object' ? value : {}) as Record<string, unknown>;

/** Restate the saved audit arithmetic; returns null rather than a partial or estimated formula. */
function savedRateFormula(audit: Record<string, unknown>) {
    const inputs = record(audit.inputs);
    const parts = record(audit.components);
    const beta = inputs.beta;
    if (audit.rateType === 'COST_OF_EQUITY') {
        const terms = [pct(inputs.riskFreeRate), pct(inputs.erp), pct(audit.selectedRate)];
        if (typeof beta !== 'number' || !Number.isFinite(beta) || terms.includes(null)) return null;
        return `${terms[0]} risk-free + ${Number(beta.toFixed(2))} beta × ${terms[1]} equity risk premium = ${terms[2]}`;
    }
    const terms = [pct(parts.equityWeight), pct(parts.costOfEquity), pct(parts.debtWeight), pct(parts.costOfDebtAfterTax), pct(audit.selectedRate)];
    if (terms.includes(null)) return null;
    return `${terms[0]} equity × ${terms[1]} + ${terms[2]} debt × ${terms[3]} after tax = ${terms[4]}`;
}

/** Read the saved API rate; an input audit is not proof that its evidence was reviewed. */
export function savedValuationRate(projection?: Projection | null) {
    const rate = projection?.globalSettings?.discountRate;
    const audit = projection?.analyticsLog?.valuationModel?.discountRateAudit;
    const knownType = audit?.rateType === 'WACC' || audit?.rateType === 'COST_OF_EQUITY';
    const available = typeof rate === 'number' && Number.isFinite(rate);
    return {
        value: available ? `${Number(rate.toFixed(2))}%` : '—',
        label: knownType ? audit.rateType === 'WACC' ? 'WACC' : 'Cost of Equity' : 'Discount Rate',
        topicId: knownType ? audit.rateType === 'WACC' ? 'wacc' : 'costOfEquity' : 'discountRate',
        status: !available ? 'No saved valuation rate' : knownType
            ? 'Input audit saved; evidence review required' : 'Rate basis unverified',
        auditDate: audit?.asOf,
        formula: knownType ? savedRateFormula(audit) : null,
        rationale: knownType && typeof record(audit.inputs).rationale === 'string'
            ? (record(audit.inputs).rationale as string) : null,
    };
}
