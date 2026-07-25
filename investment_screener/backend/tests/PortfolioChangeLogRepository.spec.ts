import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { PortfolioChangeLogRepository } from '../src/services/PortfolioChangeLogRepository';

describe('PortfolioChangeLogRepository', () => {
    let repo: PortfolioChangeLogRepository;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `change-log-repo-test-${Date.now()}-${Math.random()}.sqlite`);
        repo = new PortfolioChangeLogRepository(dbPath);
    });

    afterEach(() => {
        repo.close();
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('returns empty list when no entries exist', () => {
        expect(repo.listEntries()).to.deep.equal([]);
    });

    it('addEntry appends, does not replace', () => {
        repo.addEntry('9.6', '2026-07-02', 'First entry.', '2026-07-02T00:00:00Z');
        repo.addEntry('9.8', '2026-07-05', 'Second entry.', '2026-07-05T00:00:00Z');
        expect(repo.listEntries()).to.have.length(2);
    });

    it('listEntries ordered by date ascending', () => {
        repo.addEntry('10.8', '2026-07-10', 'Later.', '2026-07-10T00:00:00Z');
        repo.addEntry('9.6', '2026-07-02', 'Earlier.', '2026-07-02T00:00:00Z');
        const entries = repo.listEntries();
        expect(entries[0].note).to.equal('Earlier.');
        expect(entries[1].note).to.equal('Later.');
    });
});
