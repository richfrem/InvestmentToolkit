/**
 * thesisDocumentContent.spec.ts
 *
 * Purpose: proves the thesis document route serves the written thesis only. The old generated
 * "Current Positions (Auto-Updated)" tables were frozen snapshots (stale shares, weights and
 * actions); the web app shows the live positions table instead.
 */
import { expect } from 'chai';
import { currencyView, stripGeneratedPositions } from '../../src/routes/theses';

const DOC = [
    '# Thesis', '', '## 6. Committee Decision', '', '- APPROVED', '', '---', '',
    '## Current Positions (Auto-Updated)', '', '*Auto-updated 2026-09-02 19:41 by TV sync*', '',
    '| Ticker | Shares |', '|---|---|', '| **PLTR** | 0 |', '', '**Pillar total — Actual: 0.0%**', '',
].join('\n');

describe('stripGeneratedPositions', () => {
    it('removes the generated positions section through the end of the document', () => {
        const out = stripGeneratedPositions(DOC);
        expect(out).to.contain('## 6. Committee Decision');
        expect(out).to.not.contain('Current Positions');
        expect(out).to.not.contain('PLTR');
        expect(out).to.not.contain('Auto-updated');
    });

    it('drops the trailing rule so the document does not end on a dangling divider', () => {
        expect(stripGeneratedPositions(DOC).trimEnd().endsWith('---')).to.equal(false);
    });

    it('keeps any section that follows the generated one', () => {
        const withTail = DOC + '\n## Appendix\n\nkept\n';
        const out = stripGeneratedPositions(withTail);
        expect(out).to.contain('## Appendix');
        expect(out).to.contain('kept');
        expect(out).to.not.contain('PLTR');
    });

    it('returns a document without the section unchanged', () => {
        const plain = '# Thesis\n\ntext\n';
        expect(stripGeneratedPositions(plain)).to.equal(plain);
    });
});

describe('currencyView', () => {
    const note = { asOf: '2026-10-05', markdown: '- item', updatedAt: '2026-10-05T10:00:00Z', updatedBy: 'daily-loop' };
    const today = new Date('2026-10-10T12:00:00Z');

    it('is null when the document has no note', () => {
        expect(currencyView(null, today)).to.equal(null);
    });

    it('gives the age in days and marks a note older than a week as stale', () => {
        const v = currencyView(note, today)!;
        expect(v.ageDays).to.equal(5);
        expect(v.stale).to.equal(false);
        const old = currencyView({ ...note, asOf: '2026-10-01' }, today)!;
        expect(old.ageDays).to.equal(9);
        expect(old.stale).to.equal(true);
    });

    it('carries the note text and who wrote it', () => {
        const v = currencyView(note, today)!;
        expect(v.markdown).to.equal('- item');
        expect(v.updatedBy).to.equal('daily-loop');
    });

    it('never reports a negative age for a note dated today', () => {
        expect(currencyView({ ...note, asOf: '2026-10-10' }, today)!.ageDays).to.equal(0);
    });
});
