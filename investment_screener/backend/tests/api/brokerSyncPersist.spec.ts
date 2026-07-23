/**
 * brokerSyncPersist.spec.ts
 *
 * Purpose: proves BrokerSyncService.persistSnapshotToDb (Wave 3 Task 5.4) writes
 * real account_investment/investment rows for a TV snapshot's positions and cash
 * balances, using a tmp-scoped SQLite file — never the real domain_model.sqlite.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { persistSnapshotToDb, TVSnapshot } from '../../src/services/BrokerSyncService';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

function snapshotWith(snapshots: any[]): TVSnapshot {
    return {
        dataSource: 'tradingview-cdp',
        timestamp: new Date().toISOString(),
        accounts: [],
        snapshots,
        positions: snapshots.flatMap((s) => s.positions ?? []),
    };
}

describe('BrokerSyncService.persistSnapshotToDb', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `broker-sync-persist-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('writes real account_investment rows for positions and a CASH_USD row for balances', () => {
        const snapshot = snapshotWith([
            {
                accountType: 'TFSA',
                balances: { cashUSD: 250.5 },
                positions: [
                    { symbol: 'NVDA', quantity: 3, avgFillPrice: 800, accountType: 'TFSA', accountId: '1' },
                ],
            },
        ]);

        persistSnapshotToDb(snapshot, dbPath);

        const portfolioRepo = new PortfolioRepository(dbPath);
        const investmentRepo = new InvestmentRepository(dbPath);
        try {
            const rows = portfolioRepo.listAccountInvestments('TFSA');
            const nvdaRow = rows.find((r) => r.investment_id === 'NVDA');
            expect(nvdaRow, 'expected an NVDA account_investment row').to.not.be.undefined;
            expect(nvdaRow!.quantity).to.equal(3);
            expect(nvdaRow!.average_cost).to.equal(800);

            const cashInvestment = investmentRepo.getInvestment('CASH_USD');
            expect(cashInvestment, 'expected CASH_USD to be a real investment row').to.not.be.null;
            expect(cashInvestment!.asset_class).to.equal('CASH');

            const cashRow = rows.find((r) => r.investment_id === cashInvestment!.investment_id);
            expect(cashRow, 'expected a CASH_USD account_investment row (cash as a real investment row)').to.not.be.undefined;
            expect(cashRow!.quantity).to.equal(250.5);
        } finally {
            portfolioRepo.close();
            investmentRepo.close();
        }
    });

    it('writes an investment_price row of $1.00 for CASH_USD, not just an account_investment row', () => {
        // Regression guard (2026-07-23): getAccountMarketValues() INNER JOINs
        // account_investment against investment_price -- a CASH_USD row with no
        // matching investment_price row silently contributes $0 to the computed
        // portfolio total. persistSnapshotToDb wrote the account_investment row but
        // never the price row, so cash always dropped out of getPortfolioTotalValue().
        const snapshot = snapshotWith([
            {
                accountType: 'TFSA',
                balances: { cashUSD: 250.5 },
                positions: [],
            },
        ]);

        persistSnapshotToDb(snapshot, dbPath);

        const portfolioRepo = new PortfolioRepository(dbPath);
        const investmentRepo = new InvestmentRepository(dbPath);
        try {
            const cashInvestment = investmentRepo.getInvestment('CASH_USD');
            const cashPrice = portfolioRepo.getInvestmentPrice(cashInvestment!.investment_id);
            expect(cashPrice, 'expected an investment_price row for CASH_USD').to.not.be.null;
            expect(cashPrice!.price).to.equal(1.0);

            const total = portfolioRepo.getPortfolioTotalValue();
            expect(total, 'cash must count toward the computed portfolio total').to.equal(250.5);
        } finally {
            portfolioRepo.close();
            investmentRepo.close();
        }
    });

    it('persistSnapshotToDb writes only the SQLite dbPath — creates no portfolio.json', () => {
        // Wave 3 Task 8: persistSnapshotToDb is now syncAuto's SOLE write. It must
        // touch only the SQLite file it is given, never portfolio.json.
        const guardJson = path.join(os.tmpdir(), `portfolio-guard-${Date.now()}-${Math.random()}.json`);
        expect(fs.existsSync(guardJson)).to.equal(false);
        const snapshot = snapshotWith([
            { accountType: 'TFSA', balances: { cashUSD: 10 }, positions: [{ symbol: 'NVDA', quantity: 1, avgFillPrice: 800, accountType: 'TFSA', accountId: '1' }] },
        ]);
        persistSnapshotToDb(snapshot, dbPath);
        expect(fs.existsSync(dbPath), 'SQLite write should succeed').to.equal(true);
        expect(fs.existsSync(guardJson), 'no portfolio.json should be produced').to.equal(false);
    });

    it('syncAuto no longer writes portfolio.json (source-level regression guard)', () => {
        // A runtime syncAuto test would require mocking the TradingView CDP
        // subprocess (prohibited on critical runtime paths), so this guards the
        // reduction at the source: the removed fs.writeFileSync(PORTFOLIO_FILE,...)
        // must not reappear inside syncAuto.
        const src = fs.readFileSync(path.resolve(__dirname, '../../src/services/BrokerSyncService.ts'), 'utf-8');
        const syncAutoBody = src.slice(src.indexOf('export async function syncAuto'));
        expect(syncAutoBody).to.not.match(/fs\.writeFileSync\s*\(\s*PORTFOLIO_FILE/);
        expect(syncAutoBody).to.match(/persistSnapshotToDb\(snapshot\)/);
    });

    it('skips unrecognized non-real accounts and zero/negative-quantity positions', () => {
        const snapshot = snapshotWith([
            {
                accountType: 'MARGIN', // not TFSA/RRSP/CASH
                balances: { cashUSD: 100 },
                positions: [{ symbol: 'AAPL', quantity: 5, avgFillPrice: 150, accountType: 'MARGIN', accountId: '9' }],
            },
            {
                accountType: 'RRSP',
                balances: {},
                positions: [{ symbol: 'CLOSED', quantity: 0, avgFillPrice: 10, accountType: 'RRSP', accountId: '2' }],
            },
        ]);

        persistSnapshotToDb(snapshot, dbPath);

        const portfolioRepo = new PortfolioRepository(dbPath);
        try {
            expect(portfolioRepo.listAccountInvestments('MARGIN')).to.have.length(0);
            expect(portfolioRepo.listAccountInvestments('RRSP')).to.have.length(0);
        } finally {
            portfolioRepo.close();
        }
    });
});
