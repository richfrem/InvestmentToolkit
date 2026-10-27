import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import Database from 'better-sqlite3';
import { spawnSync } from 'child_process';
import { ProjectionRepository } from '../src/services/ProjectionRepository';
import { ProjectionSchema, Projection } from '../src/utils/zod-schemas';

function makeProjection(overrides: Partial<Projection> = {}): Projection {
    const base = {
        ticker: 'TEST',
        id: '11111111-1111-4111-8111-111111111111',
        source: 'USER' as const,
        schemaVersion: '1.2',
        version: 0, // server-assigned on save; irrelevant on input
        savedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        name: 'Test Projection',
        rationale: 'A test rationale',
        snapshot: {
            price: 100,
            currency: 'USD',
            shares: 1000,
            revenue: 5000,
            lastActualPS: 5,
            fiscalPeriod: 'TTM',
        },
        dataPreferences: { growthBasis: 'ttm' as const, marginBasis: 'ttm' as const },
        scenarios: {
            bear: { weight: 0.3, growthRate: 5, netMargin: 10, exitPE: 15, qualityMultiplier: 0.9, shareChange: 0 },
            base: { weight: 0.4, growthRate: 10, netMargin: 15, exitPE: 20, qualityMultiplier: 1, shareChange: 0 },
            bull: { weight: 0.3, growthRate: 15, netMargin: 20, exitPE: 25, qualityMultiplier: 1.1, shareChange: 0 },
        },
        globalSettings: { discountRate: 10, timeHorizon: 5 },
        analyticsLog: { note: 'passthrough field' },
    };
    return { ...base, ...overrides } as Projection;
}

describe('ProjectionRepository', () => {
    let repo: ProjectionRepository;
    let dbPath: string;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `projection-repo-test-${Date.now()}-${Math.random()}.sqlite`);
        repo = new ProjectionRepository(dbPath);
    });

    afterEach(() => {
        repo.close();
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    describe('upsertProjection', () => {
        it('assigns version 1 to a brand-new projection', () => {
            const parsed = ProjectionSchema.safeParse(makeProjection());
            expect(parsed.success).to.be.true;
            const saved = repo.upsertProjection(parsed.data as Projection);
            expect(saved.version).to.equal(1);
        });

        it('increments version on re-save of the same id', () => {
            const parsed = ProjectionSchema.safeParse(makeProjection()).data as Projection;
            const v1 = repo.upsertProjection(parsed);
            expect(v1.version).to.equal(1);

            const v2Input = { ...v1, version: v1.version };
            const v2 = repo.upsertProjection(v2Input as Projection);
            expect(v2.version).to.equal(2);
        });

        it('throws a Conflict error when incoming version is stale', () => {
            const parsed = ProjectionSchema.safeParse(makeProjection()).data as Projection;
            const v1 = repo.upsertProjection(parsed);
            expect(v1.version).to.equal(1);
            repo.upsertProjection({ ...v1 } as Projection); // now server is at version 2

            expect(() => repo.upsertProjection({ ...parsed, version: 0 } as Projection)).to.throw(/Conflict/);
        });

        it('does not collide version slots for two distinct ids on the same ticker', () => {
            const first = ProjectionSchema.safeParse(makeProjection({ id: '11111111-1111-4111-8111-111111111111' })).data as Projection;
            const second = ProjectionSchema.safeParse(makeProjection({ id: '22222222-2222-4222-8222-222222222222' })).data as Projection;

            const savedFirst = repo.upsertProjection(first);
            const savedSecond = repo.upsertProjection(second);

            expect(savedFirst.version).to.equal(1);
            expect(savedSecond.version).to.equal(2); // collision-safe: not reset to 1
            expect(savedFirst.id).to.not.equal(savedSecond.id);
        });

        // Caught live 2026-09-28 (APLD): the "existing" lookup had no ORDER BY, so a
        // re-save could compute an already-used version and ON CONFLICT DO UPDATE
        // silently replaced that row (the 2026-09-22 projection was overwritten).
        it('never overwrites an earlier version when the same id is saved repeatedly', () => {
            const parsed = ProjectionSchema.safeParse(makeProjection()).data as Projection;
            let saved = repo.upsertProjection(parsed);
            saved = repo.upsertProjection({ ...saved } as Projection);
            saved = repo.upsertProjection({ ...saved } as Projection);
            expect(saved.version).to.equal(3);
            const db = new Database(dbPath);
            const versions = db.prepare('SELECT version FROM projection_version ORDER BY version').all().map((r: any) => r.version);
            db.close();
            expect(versions).to.deep.equal([1, 2, 3]);
        });

        it("a same-id re-save never overwrites another identity's version", () => {
            const a = ProjectionSchema.safeParse(makeProjection({ id: '11111111-1111-4111-8111-111111111111' })).data as Projection;
            const b = ProjectionSchema.safeParse(makeProjection({ id: '22222222-2222-4222-8222-222222222222' })).data as Projection;
            const savedA = repo.upsertProjection(a);            // v1 (A)
            repo.upsertProjection(b);                           // v2 (B)
            const resavedA = repo.upsertProjection({ ...savedA } as Projection);
            expect(resavedA.version).to.equal(3);
            const db = new Database(dbPath);
            const rows = db.prepare('SELECT version, legacy_id FROM projection_version ORDER BY version').all() as any[];
            db.close();
            expect(rows.map(r => r.legacy_id)).to.deep.equal([a.id, b.id, a.id]);
        });

        it('persists scenarios and passthrough fields (round trips via raw_json)', () => {
            const parsed = ProjectionSchema.safeParse(makeProjection()).data as Projection;
            repo.upsertProjection(parsed);

            const [fetched] = repo.findByTicker('TEST');
            expect(fetched.scenarios.base.growthRate).to.equal(10);
            expect((fetched as any).analyticsLog.note).to.equal('passthrough field');
            expect(fetched.id).to.equal(parsed.id);
        });
    });

    describe('source column persistence (caught live 2026-08-28)', () => {
        it('writes the source column, not just raw_json — get_latest_projection_by_source (Python) filters on this column directly', () => {
            // Caught live persisting AMAT's projection: the API returned success,
            // and findByTicker (which reads raw_json) showed source correctly, but
            // plugins/portfolio-advisor/scripts/update_price_levels.py's
            // load_latest_projection() -> get_latest_projection_by_source() queries
            // the dedicated `projection_version.source` SQL column directly, not
            // raw_json — and that column was NULL for every projection ever saved
            // through this API because the INSERT statement never included it.
            const parsed = ProjectionSchema.safeParse(makeProjection({ source: 'AI_AGENT' })).data as Projection;
            repo.upsertProjection(parsed);

            const db = new Database(dbPath, { readonly: true });
            const row = db.prepare('SELECT source FROM projection_version WHERE investment_id = ?').get('TEST') as { source: string | null };
            db.close();

            expect(row.source).to.equal('AI_AGENT');
        });
    });

    describe('listProjectedTickers', () => {
        it('returns the upper-cased symbols that have a saved projection, once each', () => {
            expect(repo.listProjectedTickers()).to.deep.equal([]);
            const first = ProjectionSchema.safeParse(makeProjection({ ticker: 'NVDA' })).data as Projection;
            const v1 = repo.upsertProjection(first);
            repo.upsertProjection({ ...v1 } as Projection); // second version of the same projection
            const other = ProjectionSchema.safeParse(
                makeProjection({ ticker: 'AMD', id: '22222222-2222-4222-8222-222222222222' })
            ).data as Projection;
            repo.upsertProjection(other);
            expect(repo.listProjectedTickers()).to.deep.equal(['AMD', 'NVDA']);
        });
    });

    describe('findByTicker / findAll', () => {
        it('uses the Python decimal-rate contract even above 100% and preserves absent rates', () => {
            const script = path.resolve(__dirname, '../../../plugins/stock-valuation/scripts/persist_valuation.py');
            const payload = { symbol: 'HIGH', projection: { fair_value: 10, discount_rate: 1.20 } };
            const result = spawnSync('python3', [script, '--db', dbPath, '--payload', JSON.stringify(payload)], { encoding: 'utf8' });
            expect(result.status, result.stderr).to.equal(0);
            expect(repo.findByTicker('HIGH')[0].globalSettings.discountRate).to.equal(120);
            const db = new Database(dbPath);
            db.prepare('UPDATE projection_version SET snapshot_json = ?, analytics_log_json = ? WHERE investment_id = ?')
                .run('{}', '{}', 'HIGH');
            db.close();
            expect(repo.findByTicker('HIGH')[0].globalSettings.discountRate).to.equal(undefined);
        });

        it('serves the Python-calculated rate audit from SQLite without recalculating it', () => {
            const scripts = path.resolve(__dirname, '../../../plugins/stock-valuation/scripts');
            const inputs = { method: 'terminal_earnings', asOf: '2026-10-07', currency: 'USD',
                riskFreeRate: 0.04, beta: 1, erp: 0.06, marketCap: 800, totalDebt: 200,
                costOfDebtPreTax: 0.05, taxShieldRate: 0,
                rationale: 'Synthetic fixture rationale',
                sources: [{ date: '2026-10-07', url: 'https://example.org/fixture', use: 'Synthetic inputs' }] };
            const inputFile = `${dbPath}.inputs.json`;
            const auditFile = `${dbPath}.audit.json`;
            try {
                fs.writeFileSync(inputFile, JSON.stringify(inputs));
                const calculation = spawnSync('python3', [path.join(scripts, 'wacc.py'), '--inputs', inputFile], { encoding: 'utf8' });
                expect(calculation.status, calculation.stderr).to.equal(0);
                const audit = JSON.parse(calculation.stdout);
                fs.writeFileSync(auditFile, calculation.stdout);
                const payload = { symbol: 'AUDIT', projection: {
                    fair_value: 30, current_price: 30, discount_rate: audit.selectedRate,
                    valuationModel: { method: 'terminal_earnings' },
                    scenarios: { base: { weight: 1, price: 30 } },
                } };
                const persistence = spawnSync('python3', [path.join(scripts, 'persist_valuation.py'),
                    '--db', dbPath, '--payload', JSON.stringify(payload), '--rate-audit', auditFile], { encoding: 'utf8' });
                expect(persistence.status, persistence.stderr).to.equal(0);
                const [projection] = repo.findByTicker('AUDIT');
                expect(projection.globalSettings.discountRate).to.equal(10);
                expect((projection.analyticsLog as any).valuationModel.discountRateAudit).to.deep.equal(audit);
                expect(projection.scenarios.base.scenarioPrice).to.equal(30);
            } finally {
                for (const file of [inputFile, auditFile]) if (fs.existsSync(file)) fs.unlinkSync(file);
            }
        });

        it('normalizes the canonical Python persistence snapshot without losing scenario targets or discount settings', () => {
            const script = path.resolve(__dirname, '../../../plugins/stock-valuation/scripts/persist_valuation.py');
            const payload = { symbol: 'APLD', projection: {
                fair_value: 27.67, action: 'MAINTAIN', current_price: 25.34,
                base_revenue: 611311000, base_shares: 302387140,
                discount_rate: 0.1277, horizon: 7,
                researchReport: 'APLD_2026-10-07.md',
                scenarios: { bear: { price: 2.75 }, base: { price: 21.09 }, bull: { price: 57.7 } },
            } };
            const result = spawnSync('python3', [script, '--db', dbPath, '--payload', JSON.stringify(payload)], { encoding: 'utf8' });
            expect(result.status, result.stderr).to.equal(0);
            const [projection] = repo.findByTicker('APLD');
            expect(projection.snapshot.price).to.equal(25.34);
            expect(projection.snapshot.revenue).to.equal(611311000);
            expect(projection.snapshot.shares).to.equal(302387140);
            expect(projection.globalSettings.discountRate).to.be.closeTo(12.77, 0.00001);
            expect(projection.globalSettings.timeHorizon).to.equal(7);
            expect(projection.aiThesis?.researchReport).to.equal('APLD_2026-10-07.md');
            expect(projection.scenarios.bear.scenarioPrice).to.equal(2.75);
            expect(projection.scenarios.base.scenarioPrice).to.equal(21.09);
            expect(projection.scenarios.bull.scenarioPrice).to.equal(57.7);
        });

        it('returns an empty array for an unknown ticker', () => {
            expect(repo.findByTicker('NOPE')).to.deep.equal([]);
        });

        it('returns ONE current-state entry when the same id is saved twice (Finding 2 regression)', () => {
            // Restores the old filesystem-JSON model's semantics: re-saving the same
            // `Projection.id` replaced the array entry in place (array length = number of
            // distinct identities), it did not append a growing history. The repository
            // internally creates a new (investment_id, version) row per save, but
            // findByTicker/findAll must collapse rows sharing an identity down to the
            // single MAX-version row.
            const parsed = ProjectionSchema.safeParse(makeProjection()).data as Projection;
            const v1 = repo.upsertProjection(parsed);
            const v2 = repo.upsertProjection({ ...v1 } as Projection);

            const list = repo.findByTicker('TEST');
            expect(list).to.have.lengthOf(1);
            expect(list[0].version).to.equal(v2.version);
            expect(list[0].version).to.equal(2);
            expect(list[0].id).to.equal(parsed.id);
        });

        it('returns TWO entries when two distinct ids are saved for the same ticker (Finding 2 regression)', () => {
            const first = ProjectionSchema.safeParse(makeProjection({ id: '11111111-1111-4111-8111-111111111111' })).data as Projection;
            const second = ProjectionSchema.safeParse(makeProjection({ id: '22222222-2222-4222-8222-222222222222' })).data as Projection;

            repo.upsertProjection(first);
            repo.upsertProjection(second);

            const list = repo.findByTicker('TEST');
            expect(list).to.have.lengthOf(2);
            const ids = list.map(p => p.id).sort();
            expect(ids).to.deep.equal([first.id, second.id].sort());
        });

        it('aggregates current-state-per-identity projections across all tickers', () => {
            repo.upsertProjection(ProjectionSchema.safeParse(makeProjection({ ticker: 'AAA', id: '11111111-1111-4111-8111-111111111111' })).data as Projection);
            repo.upsertProjection(ProjectionSchema.safeParse(makeProjection({ ticker: 'BBB', id: '22222222-2222-4222-8222-222222222222' })).data as Projection);

            const all = repo.findAll();
            expect(all).to.have.lengthOf(2);
            const tickers = all.map(p => p.ticker).sort();
            expect(tickers).to.deep.equal(['AAA', 'BBB']);
        });
    });

    describe('deleteById', () => {
        it('returns false when the ticker does not exist', () => {
            expect(repo.deleteById('NOPE', 'some-id')).to.equal(false);
        });

        it('returns false when the id does not exist for a known ticker', () => {
            repo.upsertProjection(ProjectionSchema.safeParse(makeProjection()).data as Projection);
            expect(repo.deleteById('TEST', 'not-a-real-id')).to.equal(false);
        });

        it('deletes a matching projection and its scenarios', () => {
            const parsed = ProjectionSchema.safeParse(makeProjection()).data as Projection;
            repo.upsertProjection(parsed);

            expect(repo.deleteById('TEST', parsed.id)).to.equal(true);
            expect(repo.findByTicker('TEST')).to.deep.equal([]);
            // Idempotent: deleting again returns false, not found.
            expect(repo.deleteById('TEST', parsed.id)).to.equal(false);
        });
    });
});
