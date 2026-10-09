/**
 * brokerSyncStoredFallback.spec.ts
 *
 * Purpose: when TradingView is unreachable or returns no positions, BrokerSyncService serves
 * the positions stored in domain_model.sqlite (dataSource 'domain_model_sqlite') with a message
 * saying when they were last synced, and reads no portfolio.json. An empty database is reported
 * as an explicit empty state.
 *
 * Key Input Dependencies:
 *   - A temporary SQLite file seeded through PortfolioRepository / InvestmentRepository
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { storedPositionsResult } from '../../src/services/BrokerSyncService';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';

describe('BrokerSyncService stored-positions fallback', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `broker-sync-stored-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    function seed(lastSyncedAt: string) {
        const investmentRepo = new InvestmentRepository(dbPath);
        const portfolioRepo = new PortfolioRepository(dbPath);
        portfolioRepo.upsertAccount('TFSA', 'TFSA', 'TFSA');
        for (const [symbol, qty] of [['NVDA', 3], ['AMD', 10]] as const) {
            const id = investmentRepo.resolveInvestmentId(symbol, 'EQUITY', 'USD');
            portfolioRepo.upsertAccountInvestment('TFSA', id, qty, 100, qty * 100, 'USD', lastSyncedAt);
            portfolioRepo.upsertInvestmentPrice(id, 120, 'USD', lastSyncedAt);
        }
        investmentRepo.close();
        portfolioRepo.close();
    }

    it('serves the stored positions with the last sync time in the message', () => {
        seed('2026-10-08T15:30:00.000Z');
        const result = storedPositionsResult(true, dbPath);
        expect(result.dataSource).to.equal('domain_model_sqlite');
        expect(result.positionCount).to.equal(2);
        expect(result.message).to.contain('2026-10-08T15:30:00.000Z');
        expect(result.message).to.contain('TradingView connected but returned no positions');
    });

    it('says TradingView is unreachable when it is', () => {
        seed('2026-10-08T15:30:00.000Z');
        expect(storedPositionsResult(false, dbPath).message).to.contain('TradingView not reachable');
    });

    it('reports an explicit empty state for an empty database', () => {
        const result = storedPositionsResult(false, dbPath);
        expect(result.dataSource).to.equal('empty');
        expect(result.positionCount).to.equal(0);
        expect(result.message).to.contain('No positions');
    });

    it('the service source has no portfolio.json path or read', () => {
        const src = fs.readFileSync(path.resolve(__dirname, '../../src/services/BrokerSyncService.ts'), 'utf-8');
        expect(src).to.not.match(/portfolio\.json/);
        expect(src).to.not.match(/\bPORTFOLIO_FILE\b/);
        expect(src).to.not.match(/target-portfolio/);
    });
});
