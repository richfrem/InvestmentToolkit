import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { computeExchangeRateFromSnapshot, persistSnapshotToDb } from '../src/services/BrokerSyncService';
import { PortfolioRepository } from '../src/services/PortfolioRepository';

describe('BrokerSyncService exchange-rate (Wave 3 Task 8)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `broker-fx-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    const snapshot: any = {
        snapshots: [
            { accountType: 'TFSA', balances: { cashUSD: 100, totalEquityCADCombined: 6900, totalEquityUSDCombined: 5000 }, positions: [{ symbol: 'MSFT', quantity: 1, avgFillPrice: 400 }] },
            { accountType: 'RRSP', balances: { totalEquityCADCombined: 1380, totalEquityUSDCombined: 1000 }, positions: [] },
        ],
    };

    it('computes rate as sum(CAD)/sum(USD) across snapshots, mirroring helpers.ts', () => {
        // (6900 + 1380) / (5000 + 1000) = 1.38
        expect(computeExchangeRateFromSnapshot(snapshot)).to.equal(1.38);
    });

    it('returns null when no CAD/USD totals present', () => {
        expect(computeExchangeRateFromSnapshot({ snapshots: [{ accountType: 'TFSA', balances: {}, positions: [] }] } as any)).to.equal(null);
    });

    it('persistSnapshotToDb writes the computed rate into broker_exchange_rate', () => {
        persistSnapshotToDb(snapshot, dbPath);
        const repo = new PortfolioRepository(dbPath);
        try {
            expect(repo.getExchangeRate()).to.equal(1.38);
        } finally {
            repo.close();
        }
    });
});
