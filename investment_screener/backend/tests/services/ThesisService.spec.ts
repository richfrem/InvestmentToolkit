import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { ThesisService } from '../../src/services/ThesisService';
import { ProjectionService } from '../../src/services/ProjectionService';
import { PortfolioRepository } from '../../src/services/PortfolioRepository';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';
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

/**
 * Wave 3 Task 6: proves ThesisService.getPortfolioItems() reads through
 * PortfolioRepository (account_investment JOIN investment_price on a tmp-scoped
 * SQLite file) rather than opening data/portfolio.json directly. The service's
 * `dbPath` constructor param points it at the tmp file so this never touches the
 * real production domain_model.sqlite.
 */
describe('ThesisService.getPortfolioItems (Wave 3 Task 6)', () => {
    let dbPath: string;
    let thesisService: ThesisService;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `thesis-service-portfolio-test-${Date.now()}-${Math.random()}.sqlite`);
        thesisService = new ThesisService(undefined, dbPath);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('returns [] when the tmp SQLite db has no priced positions and no portfolio.json fallback data', async () => {
        // Touch the file so ensureSchema runs, but write nothing -- and since dbPath is
        // a tmp file, there is no sibling portfolio.json for the JSON fallback to find.
        const repo = new PortfolioRepository(dbPath);
        repo.close();
        const items = await thesisService.getPortfolioItems();
        expect(items).to.deep.equal([]);
    });

    it('reads per-symbol quantity/price aggregated from account_investment/investment_price, not portfolio.json', async () => {
        const investmentRepo = new InvestmentRepository(dbPath);
        const portfolioRepo = new PortfolioRepository(dbPath);
        const nvdaId = investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
        const now = new Date().toISOString();
        portfolioRepo.upsertAccount('TFSA', 'TFSA', 'TFSA');
        portfolioRepo.upsertAccount('RRSP', 'RRSP', 'RRSP');
        portfolioRepo.upsertAccountInvestment('TFSA', nvdaId, 3, 800, 2400, 'USD', now);
        portfolioRepo.upsertAccountInvestment('RRSP', nvdaId, 1, 800, 800, 'USD', now);
        portfolioRepo.upsertInvestmentPrice(nvdaId, 900, 'USD', now);
        investmentRepo.close();
        portfolioRepo.close();

        const items = await thesisService.getPortfolioItems();
        expect(items).to.have.lengthOf(1);
        expect(items[0].symbol).to.equal('NVDA');
        expect(items[0].quantity).to.equal(4); // 3 (TFSA) + 1 (RRSP), account boundaries preserved then summed
        expect(items[0].price).to.equal(900);
    });
});

describe('ThesisService.getAccountPolicy (Wave 5E cutover)', () => {
    let dbPath: string;
    let thesisService: ThesisService;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `thesis-service-policy-test-${Date.now()}-${Math.random()}.sqlite`);
        thesisService = new ThesisService(undefined, dbPath);
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    it('returns null when portfolio_policy has never been written (no account_policy.json fallback)', () => {
        const repo = new PortfolioRepository(dbPath);
        repo.close();
        const policy = (thesisService as any).getAccountPolicy();
        expect(policy).to.equal(null);
    });

    it('reads the account policy from portfolio_policy (SQLite), not account_policy.json', () => {
        const repo = new PortfolioRepository(dbPath);
        const db = (repo as any).db;
        db.prepare(
            `INSERT INTO portfolio_policy
             (policy_id, rebalance_frequency, portfolio_value_usd_target,
              max_marginal_risk_contribution_pct, max_cluster_variance_contribution_pct,
              rebalance_band_relative_pct, rebalance_band_absolute_pct,
              rebalance_band_critical_multiplier, account_preference_rules_json,
              psu_funding_rule_json, updated_at)
             VALUES ('default', 'quarterly', 30797, 25, 60, 20, 1.5, 2.0,
                     '[{"match":"default","prefer":"TFSA"}]',
                     '{"ticker":"PSU-U.TO","sameAccountOnly":true,"sharesFormula":"ceil(N * price / 100)"}',
                     '2026-07-25T00:00:00.000Z')`
        ).run();
        repo.close();

        // dbPath is a fresh tmp file -- there is deliberately no sibling account_policy.json,
        // so a correct result here proves the SQLite path is used, not a JSON fallback.
        const policy = (thesisService as any).getAccountPolicy();
        expect(policy).to.not.equal(null);
        expect(policy.bandConfig).to.deep.equal({ relativePct: 20, absolutePct: 1.5, criticalMultiplier: 2.0 });
        expect(policy.riskBudgetCaps).to.deep.equal({
            maxMarginalRiskContributionPct: 25, maxClusterVarianceContributionPct: 60,
        });
        expect(policy.accountPreferenceRules).to.deep.equal([{ match: 'default', prefer: 'TFSA' }]);
        expect(policy.psuFundingRule.ticker).to.equal('PSU-U.TO');
    });
});
