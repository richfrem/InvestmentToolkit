import { expect } from 'chai';
import { buildPortfolioSnapshot, preserveAuthoritativeTotal, computeWeightsMap, PortfolioTotals } from '../../src/utils/portfolioSnapshot';

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

    it('marks totalUSD as computed_fallback when no authoritative total is provided', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate);
        expect(result.totals.totalSource).to.equal('computed_fallback');
        expect(result.totals.totalUSD).to.equal(3300); // shares*price + cash, as before
    });

    it('prefers an authoritative total over the shares*price fallback when provided', () => {
        // TV broker's real combined equity (e.g. from getAccountTotals()) is the ground truth —
        // it differs from the shares*price+cash approximation because it includes cash the
        // holdings array doesn't track and reflects live broker-side pricing.
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate, 50000);
        expect(result.totals.totalUSD).to.equal(50000);
        expect(result.totals.totalSource).to.equal('tv_authoritative');
    });

    it('recomputes totalCAD from the authoritative total, not the shares*price sum', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate, 50000);
        expect(result.totals.totalCAD).to.equal(50000 * exchangeRate);
    });

    it('falls back to computed total when authoritative total is explicitly zero', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate, 0);
        expect(result.totals.totalSource).to.equal('computed_fallback');
        expect(result.totals.totalUSD).to.equal(3300);
    });

    it('falls back to computed total when authoritative total is null', () => {
        const result = buildPortfolioSnapshot(baseHoldings, tvSnapshot, exchangeRate, null);
        expect(result.totals.totalSource).to.equal('computed_fallback');
        expect(result.totals.totalUSD).to.equal(3300);
    });
});

describe('preserveAuthoritativeTotal', () => {
    const fallback = { totalUSD: 3300, totalCAD: 4554 };

    it('carries forward a previously-known authoritative total when no fresh one exists', () => {
        // This is the price-refresh bug: portfolio.json already holds a TV-authoritative
        // total from a prior sync, but a subsequent write (e.g. refreshing prices) has no
        // fresh broker fetch to work with. It must NOT silently replace the authoritative
        // total with the shares*price approximation.
        const existing: PortfolioTotals = {
            holdingsUSD: 9000, cashUSD: 41000, totalUSD: 50000, totalCAD: 69000,
            exchangeRate: 1.38, timestamp: '2026-07-01T00:00:00Z', totalSource: 'tv_authoritative',
        };
        const result = preserveAuthoritativeTotal(existing, fallback);
        expect(result.totalUSD).to.equal(50000);
        expect(result.totalSource).to.equal('tv_authoritative');
    });

    it('uses the computed fallback when no prior authoritative total exists', () => {
        const result = preserveAuthoritativeTotal(null, fallback);
        expect(result.totalUSD).to.equal(3300);
        expect(result.totalSource).to.equal('computed_fallback');
    });

    it('uses the computed fallback when the prior total was itself only a fallback', () => {
        const existing: PortfolioTotals = {
            holdingsUSD: 3000, cashUSD: 300, totalUSD: 3300, totalCAD: 4554,
            exchangeRate: 1.38, timestamp: '2026-07-01T00:00:00Z', totalSource: 'computed_fallback',
        };
        const result = preserveAuthoritativeTotal(existing, fallback);
        expect(result.totalSource).to.equal('computed_fallback');
    });
});

describe('computeWeightsMap', () => {
    it('divides each holding market_value by the persisted totals.totalUSD, not a recomputed sum', () => {
        // Holdings sum to 3300 by shares*price, but totals.totalUSD (e.g. TV-authoritative,
        // includes cash the holdings array doesn't) is 50000 — weights must use the latter.
        const holdings = [
            { symbol: 'AAPL', shares: 10, price: 150.0 },
            { symbol: 'MSFT', shares: 5, price: 200.0 },
        ];
        const totals: PortfolioTotals = {
            holdingsUSD: 3000, cashUSD: 47000, totalUSD: 50000, totalCAD: 69000,
            exchangeRate: 1.38, timestamp: '2026-07-01T00:00:00Z', totalSource: 'tv_authoritative',
        };
        const result = computeWeightsMap(holdings, totals);
        expect(result.AAPL).to.be.closeTo(1500 / 50000 * 100, 0.0001);
        expect(result.MSFT).to.be.closeTo(1000 / 50000 * 100, 0.0001);
    });

    it('falls back to a recomputed sum when totals is null', () => {
        const holdings = [
            { symbol: 'AAPL', shares: 10, price: 150.0 },
            { symbol: 'MSFT', shares: 5, price: 200.0 },
        ];
        const result = computeWeightsMap(holdings, null);
        expect(result.AAPL).to.be.closeTo(1500 / 2500 * 100, 0.0001);
        expect(result.MSFT).to.be.closeTo(1000 / 2500 * 100, 0.0001);
    });

    it('falls back to a recomputed sum when totals.totalUSD is zero', () => {
        const holdings = [{ symbol: 'AAPL', shares: 10, price: 150.0 }];
        const totals: PortfolioTotals = {
            holdingsUSD: 0, cashUSD: 0, totalUSD: 0, totalCAD: 0,
            exchangeRate: 1.38, timestamp: '2026-07-01T00:00:00Z', totalSource: 'computed_fallback',
        };
        const result = computeWeightsMap(holdings, totals);
        expect(result.AAPL).to.equal(100);
    });

    it('supports ticker field as an alternative to symbol', () => {
        const holdings = [{ ticker: 'NVDA', shares: 2, price: 500.0 }];
        const result = computeWeightsMap(holdings, null);
        expect(result.NVDA).to.equal(100);
    });
});
