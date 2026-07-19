import { expect } from 'chai';
import path from 'path';
import fs from 'fs';
// @ts-ignore
import Database from 'better-sqlite3';
import {
    queryLatestBriefFromLedger,
    queryBriefHistoryFromLedger,
    queryTickerConvictionFromLedger
} from '../../src/routes/dailybrief';

describe('dailybrief.ts route helpers integration tests', () => {
    const tempDbPath = path.resolve(__dirname, '../../../temp/test_intelligence_brief.sqlite');

    beforeEach(() => {
        if (fs.existsSync(tempDbPath)) {
            fs.unlinkSync(tempDbPath);
        }
        
        const dir = path.dirname(tempDbPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        // Initialize test database using better-sqlite3
        const db = new Database(tempDbPath);
        db.exec(`
            CREATE TABLE instrument (
                instrument_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                exchange TEXT,
                name TEXT NOT NULL,
                active_from TEXT,
                active_to TEXT
            );
            CREATE TABLE intelligence_event (
                event_id TEXT PRIMARY KEY,
                event_sequence INTEGER NOT NULL UNIQUE,
                instrument_id TEXT,
                event_type TEXT NOT NULL,
                effective_at TEXT NOT NULL,
                observed_at TEXT,
                ingested_at TEXT NOT NULL,
                source_id TEXT,
                confidence_score REAL,
                status TEXT NOT NULL,
                title TEXT,
                body_markdown TEXT,
                payload_json TEXT,
                supersedes_event_id TEXT,
                idempotency_key TEXT,
                content_hash TEXT
            );
        `);
        
        // Insert a mock instrument and REVIEW_DAILY events
        db.prepare("INSERT INTO instrument VALUES ('us-msft', 'MSFT', 'NASDAQ', 'Microsoft', '2026-07-18', NULL)").run();
        
        // Insert a newer daily brief
        const briefPayload1 = JSON.stringify({
            date: '2026-07-18',
            macro_regime: { regime: 'BULL' },
            conviction_scores: [
                { ticker: 'MSFT', total: 8, band: 'ACCUMULATE' }
            ],
            ta_refreshed: '2026-07-18T10:00:00Z'
        });
        db.prepare(`
            INSERT INTO intelligence_event VALUES (
                'event-db-1', 1, NULL, 'REVIEW_DAILY', '2026-07-18', NULL, '2026-07-18T10:00:00Z',
                'daily_brief', 1.0, 'ACTIVE', 'Daily Brief for 2026-07-18', 'Summary',
                ?, NULL, 'daily-brief-2026-07-18', 'hash1'
            )
        `).run(briefPayload1);

        // Insert an older daily brief
        const briefPayload2 = JSON.stringify({
            date: '2026-07-17',
            macro_regime: { regime: 'CONGESTION' },
            conviction_scores: [
                { ticker: 'MSFT', total: 5, band: 'REDUCE' }
            ],
            ta_refreshed: '2026-07-17T10:00:00Z'
        });
        db.prepare(`
            INSERT INTO intelligence_event VALUES (
                'event-db-2', 2, NULL, 'REVIEW_DAILY', '2026-07-17', NULL, '2026-07-17T10:00:00Z',
                'daily_brief', 1.0, 'ACTIVE', 'Daily Brief for 2026-07-17', 'Summary',
                ?, NULL, 'daily-brief-2026-07-17', 'hash2'
            )
        `).run(briefPayload2);

        db.close();
    });

    afterEach(() => {
        if (fs.existsSync(tempDbPath)) {
            fs.unlinkSync(tempDbPath);
        }
    });

    it('queryLatestBriefFromLedger returns the latest REVIEW_DAILY event payload', async () => {
        const result = await queryLatestBriefFromLedger(tempDbPath);
        expect(result).to.not.be.null;
        expect(result.date).to.equal('2026-07-18');
        expect(result.macro_regime.regime).to.equal('BULL');
        expect(result.conviction_scores[0].total).to.equal(8);
    });

    it('queryBriefHistoryFromLedger returns mapped metadata for all available events sorted descending', async () => {
        const result = await queryBriefHistoryFromLedger(tempDbPath);
        expect(result).to.not.be.null;
        expect(result).to.have.length(2);
        expect(result![0].date).to.equal('2026-07-18');
        expect(result![0].regime).to.equal('BULL');
        expect(result![0].accum_count).to.equal(1);
        expect(result![0].reduce_count).to.equal(0);
        
        expect(result![1].date).to.equal('2026-07-17');
        expect(result![1].regime).to.equal('CONGESTION');
        expect(result![1].accum_count).to.equal(0);
        expect(result![1].reduce_count).to.equal(1);
    });

    it('queryTickerConvictionFromLedger returns historical conviction scores for one ticker sorted ascending', async () => {
        const result = await queryTickerConvictionFromLedger('MSFT', tempDbPath);
        expect(result).to.not.be.null;
        expect(result).to.have.length(2);
        expect(result![0].date).to.equal('2026-07-17');
        expect(result![0].total).to.equal(5);
        expect(result![0].band).to.equal('REDUCE');
        
        expect(result![1].date).to.equal('2026-07-18');
        expect(result![1].total).to.equal(8);
        expect(result![1].band).to.equal('ACCUMULATE');
    });
});
