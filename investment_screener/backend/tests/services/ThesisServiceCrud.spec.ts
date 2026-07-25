import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { ThesisService } from '../../src/services/ThesisService';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';
import { PriceLevelRepository } from '../../src/services/PriceLevelRepository';
import { PortfolioChangeLogRepository } from '../../src/services/PortfolioChangeLogRepository';

/**
 * Wave 8: proves ThesisService.getThesis()/saveThesis()/updateHolding()/
 * addHolding()/removeHolding()/replaceHoldings() read and write
 * domain_model.sqlite (investment, strategy_pillar, price_level_set/tier,
 * portfolio_change_log tables), replacing the retired
 * data/theses/target-portfolio.json Thesis document.
 */
describe('ThesisService CRUD (Wave 8 SQLite cutover)', () => {
    let dbPath: string;
    let service: ThesisService;

    beforeEach(() => {
        dbPath = path.join(os.tmpdir(), `thesis-service-crud-test-${Date.now()}-${Math.random()}.sqlite`);
        service = new ThesisService(undefined as any, dbPath);

        const investmentRepo = new InvestmentRepository(dbPath);
        (investmentRepo as any).db
            .prepare(`INSERT INTO strategy_pillar (pillar_id, name, target_weight) VALUES ('compute', 'Compute', 40)`)
            .run();
        investmentRepo.resolveInvestmentId('NVDA', 'EQUITY', 'USD');
        investmentRepo.updateThesisFields('NVDA', {
            name: 'NVIDIA Corporation', pillarId: 'compute', targetWeight: 10,
            thesisForInclusion: 'AI compute leader.', role: 'accumulate', agentRationale: 'DCF BUY.',
        });
        investmentRepo.close();

        const priceLevelRepo = new PriceLevelRepository(dbPath);
        priceLevelRepo.replacePriceLevels(
            'NVDA', '1.0', '2026-07-01T00:00:00Z', 'dcf', null,
            [{ tier: 1, price: 150, action: 'accumulate', orderType: 'limit', basis: 'DCF', source: 'dcf', sourceDate: '2026-07-01', status: 'active' }],
            [], null, 140
        );
        priceLevelRepo.close();
    });

    afterEach(() => {
        for (const suffix of ['', '-wal', '-shm']) {
            const p = dbPath + suffix;
            if (fs.existsSync(p)) fs.unlinkSync(p);
        }
    });

    describe('getThesis', () => {
        it('returns null for a non-canonical id', async () => {
            expect(await service.getThesis('some-other-id')).to.equal(null);
        });

        it('assembles the thesis document from SQLite', async () => {
            const thesis = await service.getThesis('target-portfolio');
            expect(thesis).to.not.equal(null);
            const nvda = thesis!.holdings.find(h => h.ticker === 'NVDA');
            expect(nvda).to.not.equal(undefined);
            expect(nvda!.targetWeight).to.equal(10);
            expect(nvda!.pillarId).to.equal('compute');
            expect(nvda!.role).to.equal('accumulate');
            expect(nvda!.thesisForInclusion).to.equal('AI compute leader.');
            expect(nvda!.priceLevels!.buyTiers![0].price).to.equal(150);
            expect(nvda!.targetEntryPrice).to.equal(140);
        });

        it('does not read data/theses/target-portfolio.json at all (source-level guard)', () => {
            const src = fs.readFileSync(
                path.resolve(__dirname, '../../src/services/ThesisService.ts'), 'utf-8'
            );
            expect(src).to.not.match(/getFilePath/);
            expect(src).to.not.match(/THESES_DIR/);
        });
    });

    describe('listTheses', () => {
        it('returns the single canonical thesis entry', async () => {
            const theses = await service.listTheses();
            expect(theses).to.have.length(1);
            expect(theses[0].id).to.equal('target-portfolio');
        });

        it('returns empty array when no thesis holdings exist yet', async () => {
            const emptyDbPath = path.join(os.tmpdir(), `thesis-empty-${Date.now()}.sqlite`);
            const emptyService = new ThesisService(undefined as any, emptyDbPath);
            try {
                expect(await emptyService.listTheses()).to.deep.equal([]);
            } finally {
                for (const suffix of ['', '-wal', '-shm']) {
                    const p = emptyDbPath + suffix;
                    if (fs.existsSync(p)) fs.unlinkSync(p);
                }
            }
        });
    });

    describe('updateHolding', () => {
        it('writes the updated target weight to investment.target_weight', async () => {
            // NVDA is the only holding in this fixture -- target weights must
            // sum to 100% for validation to pass (matches the schema's real
            // "Holding target weights must sum to 100%" refinement).
            await service.updateHolding('target-portfolio', 'NVDA', { targetWeight: 100 } as any);
            const investmentRepo = new InvestmentRepository(dbPath);
            const row = investmentRepo.getInvestment('NVDA');
            investmentRepo.close();
            expect(row!.target_weight).to.equal(100);
        });
    });

    describe('addHolding', () => {
        it('writes a new holding into investment', async () => {
            const investmentRepo = new InvestmentRepository(dbPath);
            investmentRepo.resolveInvestmentId('AMD', 'EQUITY', 'USD');
            investmentRepo.close();

            // NVDA (10%) + AMD (90%) = 100%, satisfying the schema's sum refinement.
            await service.addHolding('target-portfolio', {
                ticker: 'AMD', name: 'AMD', pillarId: 'compute', targetWeight: 90,
                role: 'accumulate', thesisForInclusion: 'Diversification.',
            } as any);

            const thesis = await service.getThesis('target-portfolio');
            const amd = thesis!.holdings.find(h => h.ticker === 'AMD');
            expect(amd!.targetWeight).to.equal(90);
        });

        it('throws if the holding already exists', async () => {
            let threw = false;
            try {
                await service.addHolding('target-portfolio', { ticker: 'NVDA', name: 'NVDA', targetWeight: 1 } as any);
            } catch {
                threw = true;
            }
            expect(threw).to.equal(true);
        });
    });

    describe('removeHolding', () => {
        it('zeroes target_weight rather than deleting the investment row', async () => {
            await service.removeHolding('target-portfolio', 'NVDA');
            const investmentRepo = new InvestmentRepository(dbPath);
            const row = investmentRepo.getInvestment('NVDA');
            investmentRepo.close();
            expect(row).to.not.equal(null); // row still exists
            expect(row!.target_weight).to.equal(0);
        });
    });

    describe('deleteThesis', () => {
        it('is a no-op that returns false (single-document architecture)', async () => {
            expect(await service.deleteThesis('target-portfolio')).to.equal(false);
            // Holding must be untouched
            const thesis = await service.getThesis('target-portfolio');
            expect(thesis!.holdings.find(h => h.ticker === 'NVDA')).to.not.equal(undefined);
        });
    });
});
