/**
 * reviewCommand.test.ts
 *
 * Purpose:
 *     The "New Review" buttons (AIAnalysisModal, AIThesisSummary) copied the
 *     retired `/guide-valuation` command; the skill was renamed to
 *     `/update-stock-analysis` on 2026-08-28.
 *
 * Layer: Frontend / Utils (vitest)
 */
import { describe, it, expect } from 'vitest';
import { newReviewCommand } from './reviewCommand';

describe('newReviewCommand', () => {
    it('uses the current update-stock-analysis command', () => {
        expect(newReviewCommand('APLD')).toBe('/update-stock-analysis APLD');
    });
});
