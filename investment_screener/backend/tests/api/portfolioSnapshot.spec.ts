import { expect } from 'chai';
import { buildPortfolioSnapshot } from '../../src/utils/portfolioSnapshot';

const baseHoldings = [
    { symbol: 'AAPL', shares: 10, price: 150.0 },
    { symbol: 'MSFT', shares: 5, price: 200.0 },
];

const tvSnapshot = {
    snapshots: [
        { balances: { cashUSD: 500, totalEquityUSDCombined: 2000 } },
        { balances: { cashUSD: 300, totalEquityUSDCombined: 1000 } },
    ],
};

const exchangeRate = 1.38;

describe('buildPortfolioSnapshot', () => {
    it('adds market_value to each holding (shares * price)', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.holdings[0].market_value).to.equal(1500);
        expect(result.holdings[1].market_value).to.equal(1000);
    });

    it('preserves all existing holding fields', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.holdings[0].symbol).to.equal('AAPL');
        expect(result.holdings[0].shares).to.equal(10);
        expect(result.holdings[0].price).to.equal(150.0);
    });

    it('sums holdingsUSD from market_value', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.totals.holdingsUSD).to.equal(2500);
    });

    it('excludes USD_CASH entries from holdingsUSD', () => {
        const holdingsWithCash = [
            ...baseHoldings,
            { symbol: 'USD_CASH', shares: 1000, price: 1 },
        ];
        const result = buildPortfolioSnapshot(holdingsWithCash, tvSnapshot, exchangeRate);
        expect(result.totals.holdingsUSD).to.equal(2500);
    });

    it('sums cashUSD from all TV snapshot account balances', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.totals.cashUSD).to.equal(800);
    });

    it('computes totalUSD as holdingsUSD + cashUSD', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.totals.totalUSD).to.equal(3300);
    });

    it('computes totalCAD as totalUSD * exchangeRate', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.totals.totalCAD).to.equal(3300 * 1.38);
    });

    it('stores exchangeRate in totals', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.totals.exchangeRate).to.equal(1.38);
    });

    it('includes a timestamp in totals', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.totals.timestamp).to.be.a('string');
        expect(new Date(result.totals.timestamp).getTime()).to.be.closeTo(Date.now(), 2000);
    });

    it('handles missing cashUSD in snapshot balances gracefully', () => {
        const snapshotNoCash = { snapshots: [{ balances: {} }] };
        const result = buildPortfolioSnapshot(baseHoldings, snapshotNoCash, exchangeRate);
        expect(result.totals.cashUSD).to.equal(0);
        expect(result.totals.totalUSD).to.equal(2500);
    });

    it('handles empty snapshots array gracefully', () => {
        const snapshotEmpty = { snapshots: [] };
        const result = buildPortfolioSnapshot(baseHoldings, snapshotEmpty, exchangeRate);
        expect(result.totals.cashUSD).to.equal(0);
    });

    it('falls back to USD_CASH entry in holdings when TV snapshot has no cash or is empty', () => {
        const holdingsWithCash = [
            ...baseHoldings,
            { symbol: 'USD_CASH', shares: 5261.52, price: 1 }
        ];
        const snapshotEmpty = { snapshots: [] };
        const result = buildPortfolioSnapshot(holdingsWithCash, snapshotEmpty, exchangeRate);
        expect(result.totals.cashUSD).to.equal(5261.52);
        expect(result.totals.totalUSD).to.equal(2500 + 5261.52);
    });
});
