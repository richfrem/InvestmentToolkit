import { expect } from 'chai';
import { computeStrategyAllocation } from '../../src/utils/strategyAllocation';

describe('computeStrategyAllocation', () => {
    const mockThesis = {
        pillars: [
            { id: 'compute', name: 'ASI / Compute — Chips' },
            { id: 'sovfin', name: 'Sovereign Finance / Digital' },
            { id: 'datainfra', name: 'Data Infra / Supply Chain' },
        ],
        holdings: [
            { ticker: 'AAPL', pillarId: 'compute', subStrategyId: 'sa-asi-race' },
            { ticker: 'MSFT', pillarId: 'datainfra', subStrategyId: 'sa-asi-race' },
            { ticker: 'COIN', pillarId: 'sovfin', subStrategyId: 'sovereign-finance' },
        ],
    };

    const mockPositions = [
        { symbol: 'AAPL', shares: 10, price: 150.0, book_price: 140.0, sector: 'Technology' },
        { symbol: 'MSFT', shares: 5, price: null as any, book_price: 200.0, sector: 'Technology' }, // price is null, should fall back to book_price
        { symbol: 'COIN', shares: 5, price: 180.0, book_price: 190.0, sector: 'Cryptocurrency' },
        { symbol: 'USD_CASH', shares: 1000.0, price: 1.0, book_price: 1.0, sector: 'Cash' },
    ];

    it('falls back to book_price when price is null or undefined', () => {
        const totals = { totalUSD: 4300, holdingsUSD: 3300, cashUSD: 1000, totalCAD: 5934, exchangeRate: 1.38, timestamp: '2026-05-26T00:00:00Z' };
        const result = computeStrategyAllocation(mockPositions, totals, mockThesis);

        // MSFT value should be 5 * 200 = 1000 (using book_price fallback)
        const datainfra = result.allocation.find((a: any) => a.id === 'datainfra');
        expect(datainfra).to.not.be.undefined;
        expect(datainfra!.valueUSD).to.equal(1000);

        // AAPL value should be 10 * 150 = 1500
        const compute = result.allocation.find((a: any) => a.id === 'compute');
        expect(compute).to.not.be.undefined;
        expect(compute!.valueUSD).to.equal(1500);

        // COIN value should be 5 * 180 = 900
        const sovfin = result.allocation.find((a: any) => a.id === 'sovfin');
        expect(sovfin).to.not.be.undefined;
        expect(sovfin!.valueUSD).to.equal(900);
    });

    it('uses totals.totalUSD as totalUSD when available', () => {
        const totals = { totalUSD: 4500, holdingsUSD: 3500, cashUSD: 1000, totalCAD: 6210, exchangeRate: 1.38, timestamp: '2026-05-26T00:00:00Z' }; // Authoritative totalUSD is 4500
        const result = computeStrategyAllocation(mockPositions, totals, mockThesis);

        expect(result.totalUSD).to.equal(4500);
        // AAPL pct relative to 4500: (1500 / 4500) * 100 = 33.33%
        const compute = result.allocation.find((a: any) => a.id === 'compute');
        expect(compute!.pct).to.be.closeTo(33.33, 0.1);
    });

    it('falls back to sum of positions when totals is not available', () => {
        const result = computeStrategyAllocation(mockPositions, null, mockThesis);

        // Sum of positions: AAPL(1500) + MSFT(1000) + COIN(900) + USD_CASH(1000) = 4400
        expect(result.totalUSD).to.equal(4400);

        // AAPL pct relative to 4400: (1500 / 4400) * 100 = 34.09%
        const compute = result.allocation.find((a: any) => a.id === 'compute');
        expect(compute!.pct).to.be.closeTo(34.09, 0.1);
    });
});
