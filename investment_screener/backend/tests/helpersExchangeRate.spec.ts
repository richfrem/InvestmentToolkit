import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { getLiveUsdCadRate } from '../src/utils/helpers';
import { PortfolioRepository } from '../src/services/PortfolioRepository';

describe('getLiveUsdCadRate (Wave 3 Task 8 — SQLite-sourced)', () => {
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `helpers-fx-test-${Date.now()}-${Math.random()}.sqlite`);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('falls back to the static fallback when no rate has been synced', async () => {
        // Initialize an empty DB (no broker_exchange_rate row).
        new PortfolioRepository(dbPath).close();
        expect(await getLiveUsdCadRate(1.38, dbPath)).to.equal(1.38);
    });

    it('returns the stored rate exactly when synced', async () => {
        const repo = new PortfolioRepository(dbPath);
        repo.upsertExchangeRate(1.4012, '2026-07-20T00:00:00.000Z');
        repo.close();
        expect(await getLiveUsdCadRate(1.38, dbPath)).to.equal(1.4012);
    });
});
