import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { PriceLevelRepository } from '../src/services/PriceLevelRepository';

describe('PriceLevelRepository', () => {
    let repo: PriceLevelRepository;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `price-level-repo-test-${Date.now()}-${Math.random()}.sqlite`);
        repo = new PriceLevelRepository(dbPath);
    });

    afterEach(() => {
        repo.close();
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('returns null for an investment with no price levels', () => {
        expect(repo.getPriceLevels('NVDA')).to.equal(null);
    });

    it('round-trips buy/sell tiers, stop loss, and target entry price', () => {
        repo.replacePriceLevels(
            'NVDA', '1.0', '2026-07-01T00:00:00Z', 'dcf',
            'DCF-derived tiers',
            [{ tier: 1, price: 100, action: 'accumulate', trimPct: null, orderType: 'limit', basis: 'DCF base', source: 'dcf', sourceDate: '2026-07-01', condition: null, status: 'active' }],
            [{ tier: 1, price: 200, action: 'trim', trimPct: 25, orderType: 'limit', basis: 'DCF bull', source: 'dcf', sourceDate: '2026-07-01', condition: null, status: 'active' }],
            { price: 80, basis: 'thesis breaker', source: 'dcf', sourceDate: '2026-07-01', type: 'thesis_breaker', status: 'active' },
            95
        );

        const result = repo.getPriceLevels('NVDA')!;
        expect(result).to.not.equal(null);
        expect(result.buyTiers).to.have.length(1);
        expect(result.buyTiers[0].price).to.equal(100);
        expect(result.sellTiers).to.have.length(1);
        expect(result.sellTiers[0].trimPct).to.equal(25);
        expect(result.stopLoss!.price).to.equal(80);
        expect(result.stopLoss!.type).to.equal('thesis_breaker');
        expect(result.targetEntryPrice).to.equal(95);
    });

    it('replacePriceLevels fully replaces the prior set (full-rewrite semantics)', () => {
        repo.replacePriceLevels('NVDA', '1.0', null, null, null, [{ tier: 1, price: 100 }], [], null, null);
        repo.replacePriceLevels('NVDA', '1.0', null, null, null, [{ tier: 1, price: 111 }], [], null, null);

        const result = repo.getPriceLevels('NVDA')!;
        expect(result.buyTiers).to.have.length(1);
        expect(result.buyTiers[0].price).to.equal(111);
    });

    it('handles no stop loss / no target entry gracefully', () => {
        repo.replacePriceLevels('NVDA', '1.0', null, null, null, [], [], null, null);
        const result = repo.getPriceLevels('NVDA')!;
        expect(result.stopLoss).to.equal(null);
        expect(result.targetEntryPrice).to.equal(null);
    });
});
