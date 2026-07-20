import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { execFileSync } from 'child_process';
import { InvestmentRepository } from '../src/services/InvestmentRepository';
import { DOMAIN_MODEL_DB_FILE } from '../src/utils/paths';

describe('InvestmentRepository', () => {
    let repo: InvestmentRepository;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `investment-repo-test-${Date.now()}-${Math.random()}.sqlite`);
        repo = new InvestmentRepository(dbPath);
    });

    afterEach(() => {
        repo.close();
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    describe('listThesisHoldings', () => {
        it('only returns rows with a non-null target_weight, mapped to the JSON holding shape', () => {
            repo.resolveInvestmentId('HOLD1');
            repo.resolveInvestmentId('NOWEIGHT');

            // Direct SQL to set up fixture rows without a dedicated setter (this
            // repository intentionally only exposes setWatchlisted() as a writer
            // today — full field updates are Task 10/11's Python-side concern).
            const db = (repo as any).db;
            db.prepare(`INSERT INTO strategy_pillar (pillar_id, name, target_weight) VALUES ('compute', 'Compute', 10)`).run();
            db.prepare(`INSERT INTO sub_strategy (sub_strategy_id, pillar_id, name) VALUES ('sa-asi-race', 'compute', 'ASI Race')`).run();
            db.prepare(
                `UPDATE investment SET name=?, pillar_id=?, sub_strategy_id=?, lifecycle_status=?,
                 target_weight=?, thesis_for_inclusion=?, agent_rationale=? WHERE symbol=?`
            ).run('Holding One', 'compute', 'sa-asi-race', 'accumulate', 5.5, 'Thesis text', 'Rationale text', 'HOLD1');

            const holdings = repo.listThesisHoldings();
            expect(holdings.map(h => h.ticker)).to.deep.equal(['HOLD1']);
            expect(holdings[0]).to.deep.equal({
                ticker: 'HOLD1',
                name: 'Holding One',
                pillarId: 'compute',
                subStrategyId: 'sa-asi-race',
                role: 'accumulate',
                targetWeight: 5.5,
                thesisForInclusion: 'Thesis text',
                agentRationale: 'Rationale text',
            });
        });
    });

    describe('listWatchlisted', () => {
        it('returns only is_watchlisted=1 rows as {ticker, addedAt}', () => {
            repo.setWatchlisted('WL1', true, '2026-01-01T00:00:00.000Z');
            repo.setWatchlisted('WL2', false, null);

            const list = repo.listWatchlisted();
            expect(list).to.deep.equal([{ ticker: 'WL1', addedAt: '2026-01-01T00:00:00.000Z' }]);
        });
    });

    describe('listPillars', () => {
        it('maps strategy_pillar rows to {id, name, targetWeight}', () => {
            const db = (repo as any).db;
            db.prepare(`INSERT INTO strategy_pillar (pillar_id, name, target_weight) VALUES (?, ?, ?)`)
                .run('compute', 'ASI / Compute — Chips', 9.5207);

            const pillars = repo.listPillars();
            expect(pillars).to.deep.equal([{ id: 'compute', name: 'ASI / Compute — Chips', targetWeight: 9.5207 }]);
        });
    });

    // ── HIGHEST-RISK TEST: CLAUDE.md rule #8 (standingDecision anchor) ─────────
    // DCF must never silently override the standing decision. This asserts the
    // TS read path (getInvestment(), used by WatchlistService/InvestmentRepository
    // consumers) returns standing_decision_* fields byte-for-byte identical to an
    // INDEPENDENT ground truth: a raw sqlite3 CLI query against the same physical
    // domain_model.sqlite file, run out-of-process via Python — not through any of
    // this repository's own code, so the comparison cannot be circular.
    describe('standingDecision byte-for-byte parity (real domain_model.sqlite)', () => {
        it('getInvestment() matches an independent ground-truth query for a real ticker', function () {
            if (!fs.existsSync(DOMAIN_MODEL_DB_FILE)) {
                this.skip();
                return;
            }

            const groundTruthJson = execFileSync('python3', [
                '-c',
                `
import sqlite3, json
c = sqlite3.connect("${DOMAIN_MODEL_DB_FILE}")
row = c.execute(
    "SELECT investment_id, standing_decision_type, standing_decision_reason, "
    "standing_decision_source, standing_decision_review FROM investment "
    "WHERE standing_decision_type IS NOT NULL LIMIT 1"
).fetchone()
print(json.dumps(row))
`,
            ]).toString().trim();
            const [investmentId, type, reason, source, review] = JSON.parse(groundTruthJson);
            expect(investmentId, 'no ticker with a standing decision found in the real DB').to.not.be.undefined;

            const liveRepo = new InvestmentRepository(DOMAIN_MODEL_DB_FILE);
            let row;
            try {
                row = liveRepo.getInvestment(investmentId);
            } finally {
                liveRepo.close();
            }

            expect(row, `getInvestment(${investmentId}) returned null`).to.not.be.null;
            expect(row!.standing_decision_type).to.equal(type);
            expect(row!.standing_decision_reason).to.equal(reason);
            expect(row!.standing_decision_source).to.equal(source);
            expect(row!.standing_decision_review).to.equal(review);

            // eslint-disable-next-line no-console
            console.log(`[standingDecision parity] ticker=${investmentId} type=${type}`);
        });
    });
});
