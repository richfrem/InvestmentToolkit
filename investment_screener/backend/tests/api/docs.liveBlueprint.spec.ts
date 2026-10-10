/**
 * docs.liveBlueprint.spec.ts
 *
 * Purpose: proves the master thesis is served as prose with a marker where the live positions go.
 * The generated "Portfolio Blueprint" block was a frozen snapshot of every position; the web app
 * shows live tables at the marker instead.
 */
import { expect } from 'chai';
import { LIVE_POSITIONS_MARKER, replaceGeneratedBlueprint } from '../../src/routes/docs';

const DOC = [
    '## III. Portfolio Weights', '', 'note', '', '## IV. Portfolio Blueprint', '',
    '<!-- AUTO_UPDATE_START: portfolio_blueprint -->', '*Generated 2026-10-09*', '| **ZS** | TRIM | 6.08% |', '<!-- AUTO_UPDATE_END: portfolio_blueprint -->',
    '', '## V. Risk Factors', '', 'risks',
].join('\n');

describe('replaceGeneratedBlueprint', () => {
    it('replaces the generated block, markers included, with the live-positions marker', () => {
        const out = replaceGeneratedBlueprint(DOC);
        expect(out).to.contain(LIVE_POSITIONS_MARKER);
        expect(out).to.not.contain('AUTO_UPDATE');
        expect(out).to.not.contain('ZS');
        expect(out).to.not.contain('Generated 2026');
    });

    it('keeps the headings and prose around the block', () => {
        const out = replaceGeneratedBlueprint(DOC);
        expect(out).to.contain('## IV. Portfolio Blueprint');
        expect(out).to.contain('## V. Risk Factors');
        expect(out.indexOf('## IV.')).to.be.lessThan(out.indexOf(LIVE_POSITIONS_MARKER));
        expect(out.indexOf(LIVE_POSITIONS_MARKER)).to.be.lessThan(out.indexOf('## V.'));
    });

    it('leaves a document with no generated block unchanged, marker included', () => {
        const plain = '## IV. Portfolio Blueprint\n\n' + LIVE_POSITIONS_MARKER + '\n\n## V. Risk\n';
        expect(replaceGeneratedBlueprint(plain)).to.equal(plain);
        expect(replaceGeneratedBlueprint('# Thesis\n\ntext\n')).to.equal('# Thesis\n\ntext\n');
    });

    it('ignores an unterminated block rather than swallowing the rest of the document', () => {
        const broken = '## IV.\n<!-- AUTO_UPDATE_START: portfolio_blueprint -->\nrows\n## V. Risk\n';
        expect(replaceGeneratedBlueprint(broken)).to.equal(broken);
    });
});
