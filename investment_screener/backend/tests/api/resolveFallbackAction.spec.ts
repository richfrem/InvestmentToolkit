/**
 * Purpose: regression coverage for canonical records replacing invented fallback actions.
 * Layer: API bridge integration. Usage: mocha -r ts-node/register tests/api/resolveFallbackAction.spec.ts
 * Functions: seed a real isolated DB, invoke getRecommendations through the Python bridge.
 * Key input dependencies: SQLite repositories, recommendation.py symlink, Python.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import Database from 'better-sqlite3';
import { InvestmentRepository } from '../../src/services/InvestmentRepository';
import { ThesisService } from '../../src/services/ThesisService';
import { getRecommendations } from '../../src/utils/helpers';

describe('canonical recommendation bridge', () => {
    it('returns actual records and never derives actions from targets', async () => {
        const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'recommendations-'));
        const dbPath = path.join(directory, 'domain_model.sqlite');
        const investments = new InvestmentRepository(dbPath);
        const id = investments.resolveInvestmentId('BRIDGE_TEST');
        investments.close();
        const db = new Database(dbPath);
        db.prepare('UPDATE investment SET target_weight = 99 WHERE investment_id = ?').run(id);
        db.close();
        const records = await getRecommendations(dbPath);
        expect(records.BRIDGE_TEST.action).to.equal('WATCHLIST');
        expect(records.BRIDGE_TEST.held).to.equal(false);
        expect(records.BRIDGE_TEST.upside_pct).to.equal(null);
        expect(records.BRIDGE_TEST.reason).to.include('no valuation');
        const optimized = await new ThesisService(undefined, dbPath).optimizePortfolio('target-portfolio');
        expect(optimized.recommendations.BRIDGE_TEST.action).to.equal(records.BRIDGE_TEST.action);
    });
});
