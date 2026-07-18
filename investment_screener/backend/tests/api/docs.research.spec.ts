import { expect } from 'chai';
import { parseResearchFilename, DATED_FILENAME_RE, CANONICAL_FILENAME_RE } from '../../src/routes/docs';

describe('DATED_FILENAME_RE / CANONICAL_FILENAME_RE', () => {
  it('accepts a dated filename', () => {
    expect(DATED_FILENAME_RE.test('PLTR_2026-07-02.md')).to.equal(true);
  });
  it('accepts a canonical summary/timeline filename', () => {
    expect(CANONICAL_FILENAME_RE.test('PLTR.summary.md')).to.equal(true);
    expect(CANONICAL_FILENAME_RE.test('PLTR.timeline.md')).to.equal(true);
  });
  it('rejects neither shape', () => {
    expect(DATED_FILENAME_RE.test('PLTR.md')).to.equal(false);
    expect(CANONICAL_FILENAME_RE.test('PLTR_2026-07-02.md')).to.equal(false);
  });
});

describe('parseResearchFilename', () => {
  it('parses a dated filename into ticker + date', () => {
    expect(parseResearchFilename('PLTR_2026-07-02.md')).to.deep.equal({ ticker: 'PLTR', date: '2026-07-02' });
  });
  it('parses a canonical filename into ticker + null date (not undefined)', () => {
    expect(parseResearchFilename('PLTR.summary.md')).to.deep.equal({ ticker: 'PLTR', date: null });
    expect(parseResearchFilename('PLTR.timeline.md')).to.deep.equal({ ticker: 'PLTR', date: null });
  });
});
