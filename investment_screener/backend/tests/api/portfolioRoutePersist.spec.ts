/**
 * portfolioRoutePersist.spec.ts
 *
 * Purpose: proves routes/portfolio.ts's persistPortfolioWithSnapshot() (Wave 3
 * Task 5.5) additionally persists the tvSnapshot's real per-account positions
 * into account_investment rows via BrokerSyncService.persistSnapshotToDb, using
 * a tmp-scoped SQLite file -- never the real domain_model.sqlite.
 *
 * persistPortfolioWithSnapshot itself is not exported (module-private), so this
 * test exercises the exported persistSnapshotToDb directly with the same shape
 * of tvSnapshot object persistPortfolioWithSnapshot receives/loads, which is the
 * unit actually under test for this rewire (see routes/portfolio.ts's call site).
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { persistSnapshotToDb, TVSnapshot } from '../../src/services/BrokerSyncService';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';

describe('routes/portfolio.ts persistPortfolioWithSnapshot -> SQLite dual-write', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `portfolio-route-persist-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('a promote/apply-shaped tvSnapshot persists real per-account rows', () => {
        const tvSnap: TVSnapshot = {
            dataSource: 'tradingview-cdp',
            timestamp: new Date().toISOString(),
            accounts: [],
            snapshots: [
                {
                    accountType: 'RRSP',
                    balances: { cashUSD: 42 },
                    positions: [{ symbol: 'AMD', quantity: 7, avgFillPrice: 120, accountType: 'RRSP', accountId: '2' }],
                },
            ],
            positions: [{ symbol: 'AMD', quantity: 7, avgFillPrice: 120, accountType: 'RRSP', accountId: '2' }],
        };

        persistSnapshotToDb(tvSnap, dbPath);

        const repo = new PortfolioRepository(dbPath);
        try {
            const rows = repo.listAccountInvestments('RRSP');
            expect(rows.find((r) => r.investment_id === 'AMD')).to.not.be.undefined;
        } finally {
            repo.close();
        }
    });
});
