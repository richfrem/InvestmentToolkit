/**
 * Purpose: display saved valuation rates consistently without estimating rates in the browser.
 * Layer: Frontend / Presentation. Usage: savedValuationRate(projection).
 * Key Functions: savedValuationRate — stored percentage, label, help topic and audit limits.
 * Key Input Dependencies: backend Projection percentage-rate and persisted audit contract.
 */
import type { Projection } from '../services/api';

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
    };
}
