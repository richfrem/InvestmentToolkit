import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
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

        it('persists scenarios and passthrough fields (round trips via raw_json)', () => {
            const parsed = ProjectionSchema.safeParse(makeProjection()).data as Projection;
            repo.upsertProjection(parsed);

            const [fetched] = repo.findByTicker('TEST');
            expect(fetched.scenarios.base.growthRate).to.equal(10);
            expect((fetched as any).analyticsLog.note).to.equal('passthrough field');
            expect(fetched.id).to.equal(parsed.id);
        });
    });

    describe('findByTicker / findAll', () => {
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
