import { expect } from 'chai';
import path from 'path';
import fs from 'fs';
import { parseResearchFilename, DATED_FILENAME_RE, CANONICAL_FILENAME_RE } from '../../src/routes/docs';

describe('DATED_FILENAME_RE / CANONICAL_FILENAME_RE', () => {
  it('accepts a dated filename', () => {
    expect(DATED_FILENAME_RE.test('PLTR_2026-07-02.md')).to.equal(true);
  });
  it('accepts a canonical summary/timeline filename', () => {
    expect(CANONICAL_FILENAME_RE.test('PLTR.summary.md')).to.equal(true);
    expect(CANONICAL_FILENAME_RE.test('PLTR.timeline.md')).to.equal(true);
  });
  it('rejects neither shape', () => {
    expect(DATED_FILENAME_RE.test('PLTR.md')).to.equal(false);
    expect(CANONICAL_FILENAME_RE.test('PLTR_2026-07-02.md')).to.equal(false);
  });
});

describe('parseResearchFilename', () => {
  it('parses a dated filename into ticker + date', () => {
    expect(parseResearchFilename('PLTR_2026-07-02.md')).to.deep.equal({ ticker: 'PLTR', date: '2026-07-02' });
  });
  it('parses a canonical filename into ticker + null date (not undefined)', () => {
    expect(parseResearchFilename('PLTR.summary.md')).to.deep.equal({ ticker: 'PLTR', date: null });
    expect(parseResearchFilename('PLTR.timeline.md')).to.deep.equal({ ticker: 'PLTR', date: null });
  });
});

// @ts-ignore
import Database from 'better-sqlite3';
import { queryLatestResearchFromLedger, queryResearchListFromLedger } from '../../src/routes/docs';

describe('docs.ts ledger query helpers', () => {
    const tempDbPath = path.resolve(__dirname, '../../../temp/test_intelligence_docs.sqlite');

    beforeEach(() => {
        if (fs.existsSync(tempDbPath)) {
            fs.unlinkSync(tempDbPath);
        }
        
        const dir = path.dirname(tempDbPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

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
        
        db.prepare("INSERT INTO instrument VALUES ('us-msft', 'MSFT', 'NASDAQ', 'Microsoft', '2026-07-18', NULL)").run();
        
        db.prepare(`
            INSERT INTO intelligence_event VALUES (
                'event-doc-1', 1, 'us-msft', 'RESEARCH_IMPORT', '2026-07-18', NULL, '2026-07-18T10:00:00Z',
                'valuation', 1.0, 'ACTIVE', 'MSFT Research', 'Microsoft is growing',
                NULL, NULL, 'research-import-MSFT_2026-07-18.md', 'hash1'
            )
        `).run();
        
        db.close();
    });

    afterEach(() => {
        if (fs.existsSync(tempDbPath)) {
            fs.unlinkSync(tempDbPath);
        }
    });

    it('queryLatestResearchFromLedger retrieves research event body by filename', async () => {
        const result = await queryLatestResearchFromLedger('MSFT_2026-07-18.md', tempDbPath);
        expect(result).to.not.be.null;
        expect(result.content).to.equal('Microsoft is growing');
        expect(result.ticker).to.equal('MSFT');
        expect(result.date).to.equal('2026-07-18');
    });

    it('queryResearchListFromLedger retrieves all active research event references', async () => {
        const result = await queryResearchListFromLedger(tempDbPath);
        expect(result).to.not.be.null;
        expect(result).to.have.length(1);
        expect(result![0].filename).to.equal('MSFT_2026-07-18.md');
        expect(result![0].ticker).to.equal('MSFT');
        expect(result![0].date).to.equal('2026-07-18');
    });
});

