/**
 * brokerSyncAliases.spec.ts
 *
 * Purpose:
 *     Regression tests for broker ticker alias normalization in the TV sync
 *     merge path. TradingView's broker panel returns PSU.U.TO (dot form);
 *     the canonical thesis symbol is PSU-U.TO (hyphen form — Yahoo/TSX).
 *     The Python CDP path normalizes this, but the Express sync path
 *     (mergeIntoPortfolio) wrote the raw dot form into portfolio.json,
 *     re-creating the duplicate PSU row the user has hit repeatedly.
 *
 * Layer: Backend / Tests
 */
import { expect } from 'chai';
import { mergeIntoPortfolio, TVSnapshot } from '../../src/services/BrokerSyncService';

function snapshotWith(positions: Array<Partial<{ symbol: string; quantity: number; avgFillPrice: number; accountType: string; accountId: string }>>): TVSnapshot {
    return {
        dataSource: 'tradingview-cdp',
        timestamp: new Date().toISOString(),
        accounts: [],
        snapshots: [],
        positions: positions as TVSnapshot['positions'],
    };
}

describe('mergeIntoPortfolio — broker ticker aliases', () => {
    it('normalizes PSU.U.TO from TV to canonical PSU-U.TO', () => {
        const tv = snapshotWith([
            { symbol: 'PSU.U.TO', quantity: 53, avgFillPrice: 100.0, accountType: 'TFSA', accountId: '1' },
        ]);
        const { merged, added } = mergeIntoPortfolio(tv, []);
        const symbols = merged.map((h: any) => h.symbol);
        expect(symbols).to.include('PSU-U.TO');
        expect(symbols).to.not.include('PSU.U.TO');
        expect(added).to.include('PSU-U.TO');
    });

    it('merges TV dot-form into an existing hyphen-form holding (no duplicate, no false add/remove)', () => {
        const tv = snapshotWith([
            { symbol: 'PSU.U.TO', quantity: 56, avgFillPrice: 99.5, accountType: 'TFSA', accountId: '1' },
        ]);
        const existing = [{ symbol: 'PSU-U.TO', shares: 53, book_price: 100.0, price: 100.2 }];
        const { merged, added, removed } = mergeIntoPortfolio(tv, existing);
        const psuRows = merged.filter((h: any) => String(h.symbol).includes('PSU'));
        expect(psuRows).to.have.length(1);
        expect(psuRows[0].symbol).to.equal('PSU-U.TO');
        expect(psuRows[0].shares).to.equal(56);
        expect(added).to.not.include('PSU-U.TO');
        expect(removed).to.be.empty;
    });

    it('aggregates dot and hyphen forms across accounts into one position', () => {
        const tv = snapshotWith([
            { symbol: 'PSU.U.TO', quantity: 40, avgFillPrice: 100.0, accountType: 'TFSA', accountId: '1' },
            { symbol: 'PSU-U.TO', quantity: 16, avgFillPrice: 99.0, accountType: 'RRSP', accountId: '2' },
        ]);
        const { merged } = mergeIntoPortfolio(tv, []);
        const psuRows = merged.filter((h: any) => String(h.symbol).includes('PSU'));
        expect(psuRows).to.have.length(1);
        expect(psuRows[0].shares).to.equal(56);
    });

    it('leaves non-aliased symbols untouched', () => {
        const tv = snapshotWith([
            { symbol: 'NVDA', quantity: 2, avgFillPrice: 800.0, accountType: 'TFSA', accountId: '1' },
        ]);
        const { merged } = mergeIntoPortfolio(tv, []);
        expect(merged.map((h: any) => h.symbol)).to.include('NVDA');
    });
});
