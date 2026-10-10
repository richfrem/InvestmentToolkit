/**
 * portfolioRouteNoJsonFallback.spec.ts
 *
 * Purpose: routes/portfolio.ts and utils/paths.ts read portfolio data from domain_model.sqlite
 * only. There is no file reader, writer or fallback, no manual position-save route
 * (positions come from the broker sync), and an empty database is reported as an explicit
 * empty state rather than served from a file.
 *
 * Key Input Dependencies:
 *   - src/routes/portfolio.ts, src/utils/paths.ts, src/services/BrokerSyncService.ts (read as text)
 */
import { expect } from 'chai';
import fs from 'fs';
import path from 'path';

const read = (rel: string) => fs.readFileSync(path.resolve(__dirname, '../../', rel), 'utf-8');

describe('portfolio route: SQLite only, no JSON fallback', () => {
    const route = read('src/routes/portfolio.ts');

    it('has no readPortfolio, PORTFOLIO_FILE or backupPortfolio', () => {
        expect(route).to.not.match(/\breadPortfolio\b/);
        expect(route).to.not.match(/\bPORTFOLIO_FILE\b/);
        expect(route).to.not.match(/\bbackupPortfolio\b/);
        expect(route).to.not.match(/portfolio\.json/);
    });

    it('has no POST / route that saves positions', () => {
        expect(route).to.not.match(/router\.post\(\s*'\/'\s*,/);
    });

    it('serves an explicit empty state, not file data, when the database has no positions', () => {
        expect(route).to.match(/dataSource:\s*dbHoldings != null \? 'domain_model_sqlite' : 'empty'/);
        expect(route).to.contain("price_source: priceSource");
        expect(route).to.contain("'empty'");
    });

    it('paths.ts exports no retired data file constant', () => {
        const paths = read('src/utils/paths.ts');
        for (const name of ['PORTFOLIO_FILE', 'THESIS_FILE', 'TARGET_PORTFOLIO_FILE']) {
            expect(paths, name).to.not.match(new RegExp(`export const ${name}\\b`));
        }
        for (const name of ['YTD_PERFORMANCE_REPORT_FILE', 'PORTFOLIO_CONFIG_FILE']) {
            expect(paths, name).to.not.match(new RegExp(`export const ${name}\\b`));
        }
    });

    it('does not hand a portfolio file path to the performance script', () => {
        expect(route).to.not.match(/portfolio_performance\.py',\s*\[PORTFOLIO_FILE\]/);
    });
});
