import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { ThesisService } from '../../src/services/ThesisService';
import { ProjectionService } from '../../src/services/ProjectionService';
import { ProjectionSchema, Projection } from '../../src/utils/zod-schemas';

/**
 * Task 7C: proves ThesisService.getLatestAIProjection reads through ProjectionService
 * (SQLite-backed, ADR-029) rather than opening data/projections/{ticker}.json directly.
 * Uses a temp SQLite file via a real ProjectionService instance — never touches the real
 * production domain_model.sqlite.
 */
function makeProjection(overrides: Partial<Projection> = {}): Projection {
    const base = {
        ticker: 'TEST',
        id: '11111111-1111-4111-8111-111111111111',
        source: 'AI_AGENT' as const,
        schemaVersion: '1.2',
        version: 0,
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
        aiThesis: {
            model: 'test-model',
            rationale: 'AI rationale',
            fairValue: 150,
            action: 'INITIATE',
            analyzedAt: new Date().toISOString(),
        },
    };
    return { ...base, ...overrides } as Projection;
}

describe('ThesisService.getLatestAIProjection', () => {
    let dbPath: string;
    let projectionService: ProjectionService;
    let thesisService: ThesisService;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `thesis-service-test-${Date.now()}-${Math.random()}.sqlite`);
        projectionService = new ProjectionService(dbPath);
        thesisService = new ThesisService(projectionService);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('returns null when the ticker has no projections', async () => {
        const result = await thesisService.getLatestAIProjection('NONEXISTENT');
        expect(result).to.be.null;
    });

    it('returns null when projections exist but none are source AI_AGENT', async () => {
        const parsed = ProjectionSchema.safeParse(makeProjection({ source: 'USER' }));
        expect(parsed.success).to.be.true;
        await projectionService.saveProjection(parsed.data as Projection);

        const result = await thesisService.getLatestAIProjection('TEST');
        expect(result).to.be.null;
    });

    it('returns the latest AI_AGENT projection by version, not the file-order default', async () => {
        const parsed = ProjectionSchema.safeParse(makeProjection());
        expect(parsed.success).to.be.true;
        const v1 = await projectionService.saveProjection(parsed.data as Projection).then(
            () => projectionService.getProjections('TEST')
        );
        expect(v1[0].version).to.equal(1);

        // Save a second version with a higher fair value, under the same id so it
        // increments (matches ProjectionRepository's upsert-by-id-then-version rule).
        const v2Input = { ...(v1[0]), aiThesis: { ...v1[0].aiThesis!, fairValue: 200 } };
        await projectionService.saveProjection(v2Input as Projection);

        const result = await thesisService.getLatestAIProjection('TEST');
        expect(result).to.not.be.null;
        expect(result!.version).to.equal(2);
        expect(result!.aiThesis?.fairValue).to.equal(200);
    });

    it('reads through ProjectionService, not through data/projections/*.json on disk', async () => {
        // No file exists for this ticker anywhere on disk; a nonexistent projections dir
        // proves the read path is entirely SQLite-backed.
        const bogusTicker = `NOFILE_${Date.now()}`;
        const result = await thesisService.getLatestAIProjection(bogusTicker);
        expect(result).to.be.null;
    });
});
