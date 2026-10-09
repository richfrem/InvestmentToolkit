/**
 * ThesisBreakerRepository.spec.ts - ThesisBreakerRepository against a real temporary SQLite database: definitions, manual status, evaluated state.
 *
 * Key Input Dependencies:
 *   - A temporary SQLite file built by the Python schema migrator
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { InvestmentRepository } from '../src/services/InvestmentRepository';
import { ThesisBreakerRepository, BreakerDefinition, BreakerState } from '../src/services/ThesisBreakerRepository';

const AUTO: BreakerDefinition = { id: 'rsi-low', type: 'auto', metric: 'rsi', operator: '<', threshold: 30, horizon: 3, note: 'oversold' };
const MANUAL: BreakerDefinition = {
    id: 'ceo-exit', type: 'manual', operator: '==', threshold: true, status: 'OK',
    statusSetAt: '2026-10-01', reviewCadenceDays: 30, note: 'CEO departure',
};
const STATE: BreakerState = {
    NVDA: {
        'rsi-low': { type: 'auto', currentValue: 22.5, conditionMet: true, currentStreak: 2,
            streakStartDate: '2026-10-08', lastEvaluatedAt: '2026-10-09T01:00:00Z', status: 'WATCHING' },
        'ceo-exit': { type: 'manual', status: 'OK', statusSetAt: '2026-10-01', reviewCadenceDays: 30,
            daysSinceReview: 8, stale: false },
    },
};

describe('ThesisBreakerRepository', () => {
    let repo: ThesisBreakerRepository;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `breaker-repo-test-${Date.now()}-${Math.random()}.sqlite`);
        const inv = new InvestmentRepository(dbPath);
        inv.resolveInvestmentId('NVDA');
        inv.resolveInvestmentId('AMD');
        inv.close();
        repo = new ThesisBreakerRepository(dbPath);
    });

    afterEach(() => {
        repo.close();
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('round-trips auto and manual definitions', () => {
        repo.upsertBreaker('NVDA', AUTO);
        repo.upsertBreaker('NVDA', MANUAL);
        expect(repo.listBreakers('NVDA')).to.deep.equal([AUTO, MANUAL]);
    });

    it('lists every ticker when no symbol is given', () => {
        repo.upsertBreaker('NVDA', AUTO);
        repo.upsertBreaker('AMD', { ...AUTO, id: 'rsi-amd' });
        const all = repo.listAllBreakers();
        expect(Object.keys(all).sort()).to.deep.equal(['AMD', 'NVDA']);
    });

    it('upsert replaces an existing breaker', () => {
        repo.upsertBreaker('NVDA', AUTO);
        repo.upsertBreaker('NVDA', { ...AUTO, threshold: 25 });
        const rows = repo.listBreakers('NVDA');
        expect(rows).to.have.length(1);
        expect(rows[0].threshold).to.equal(25);
    });

    it('rejects invalid breakers and unknown tickers', () => {
        expect(() => repo.upsertBreaker('NVDA', { ...AUTO, metric: 'bogus' })).to.throw(/metric/);
        expect(() => repo.upsertBreaker('NVDA', { ...AUTO, operator: 'in', threshold: 3 })).to.throw(/list/);
        expect(() => repo.upsertBreaker('NVDA', { ...MANUAL, status: 'BROKEN' })).to.throw(/status/);
        expect(() => repo.upsertBreaker('ZZZZ', AUTO)).to.throw(/ZZZZ/);
    });

    it('deletes a breaker with its state and rejects an unknown id', () => {
        repo.upsertBreaker('NVDA', AUTO);
        repo.upsertBreaker('NVDA', MANUAL);
        repo.replaceBreakerState(STATE);
        repo.deleteBreaker('NVDA', 'rsi-low');
        expect(repo.listBreakers('NVDA')).to.have.length(1);
        expect(Object.keys(repo.listBreakerState().NVDA)).to.deep.equal(['ceo-exit']);
        expect(() => repo.deleteBreaker('NVDA', 'rsi-low')).to.throw(/rsi-low/);
    });

    it('sets a manual status, rejecting auto breakers', () => {
        repo.upsertBreaker('NVDA', AUTO);
        repo.upsertBreaker('NVDA', MANUAL);
        repo.setManualStatus('NVDA', 'ceo-exit', 'WATCHING', 'rumour', '2026-10-09');
        const b = repo.listBreakers('NVDA').find(x => x.id === 'ceo-exit')!;
        expect(b.status).to.equal('WATCHING');
        expect(b.statusSetAt).to.equal('2026-10-09');
        expect(b.note).to.equal('CEO departure | status update 2026-10-09: rumour');
        expect(() => repo.setManualStatus('NVDA', 'rsi-low', 'OK', null)).to.throw(/manual/);
    });

    it('replaces state, round-trips it, and rejects state for an undefined breaker', () => {
        repo.upsertBreaker('NVDA', AUTO);
        expect(() => repo.replaceBreakerState(STATE)).to.throw(/ceo-exit/);
        expect(repo.listBreakerState()).to.deep.equal({});
        repo.upsertBreaker('NVDA', MANUAL);
        repo.replaceBreakerState(STATE);
        expect(repo.listBreakerState()).to.deep.equal(STATE);
    });
});
