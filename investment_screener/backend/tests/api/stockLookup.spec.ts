import { expect } from 'chai';
import { buildLookupDictionary } from '../../src/utils/stockLookup';

describe('buildLookupDictionary', () => {
    const mockHoldings = [
        { ticker: 'CBRS', name: 'Cerebras Systems Inc.', role: 'core' },
        { ticker: 'GOOG', name: 'Alphabet Inc.', role: 'core' },
        { ticker: 'META', name: 'Meta Platforms, Inc.', role: 'core' }
    ];

    it('should map exact tickers to themselves', () => {
        const dict = buildLookupDictionary(mockHoldings);
        expect(dict['CBRS']).to.equal('CBRS');
        expect(dict['GOOG']).to.equal('GOOG');
        expect(dict['META']).to.equal('META');
    });

    it('should map company names in uppercase without suffixes', () => {
        const dict = buildLookupDictionary(mockHoldings);
        expect(dict['CEREBRAS SYSTEMS']).to.equal('CBRS');
        expect(dict['ALPHABET']).to.equal('GOOG');
        expect(dict['META PLATFORMS']).to.equal('META');
    });

    it('should handle phonetic and common typos/aliases (e.g. CEREBRUS, GOOGLE, FACEBOOK)', () => {
        const dict = buildLookupDictionary(mockHoldings);
        expect(dict['CEREBRUS']).to.equal('CBRS');
        expect(dict['CEREBRAS']).to.equal('CBRS');
        expect(dict['GOOGLE']).to.equal('GOOG');
        expect(dict['FACEBOOK']).to.equal('META');
    });

    it('should normalize spaces and special characters', () => {
        const dict = buildLookupDictionary(mockHoldings);
        expect(dict['  CEREBRAS   SYSTEMS  ']).to.equal('CBRS');
    });
});
