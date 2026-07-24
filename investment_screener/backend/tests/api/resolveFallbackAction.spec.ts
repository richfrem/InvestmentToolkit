import { expect } from 'chai';
import { resolveFallbackAction } from '../../src/routes/screener';

describe('resolveFallbackAction', () => {
    it('a watched ticker always resolves to WATCHLIST', () => {
        expect(resolveFallbackAction(true, false, false)).to.equal('WATCHLIST');
        expect(resolveFallbackAction(true, true, true)).to.equal('WATCHLIST');
    });

    it('an unwatched ticker with a live holding and no thesis resolves to EXIT', () => {
        expect(resolveFallbackAction(false, true, false)).to.equal('EXIT');
    });

    it('an unwatched ticker with a live holding AND a thesis resolves to null (not EXIT)', () => {
        expect(resolveFallbackAction(false, true, true)).to.equal(null);
    });

    it('a researched-but-untracked ticker (no watch, no live holding, no thesis) resolves to null, not WATCHLIST', () => {
        expect(resolveFallbackAction(false, false, false)).to.equal(null);
    });

    it('an unwatched ticker with only a thesis (no live holding) resolves to null', () => {
        expect(resolveFallbackAction(false, false, true)).to.equal(null);
    });
});
