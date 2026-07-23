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

import { getResearchReport } from '../../src/routes/docs';

describe('getResearchReport (Wave 5A — no fs fallback for dated filenames)', () => {
    const tempDbPath = path.resolve(__dirname, '../../../temp/test_intelligence_docs_report.sqlite');
    const tempResearchDir = path.resolve(__dirname, '../../../temp/test_research_dir_report');

    function seedDb(rows: Array<{ ticker: string; effectiveAt: string; body: string }>) {
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
        rows.forEach((r, i) => {
            db.prepare(
                "INSERT INTO instrument VALUES (?, ?, 'NASDAQ', ?, '2026-01-01', NULL)"
            ).run(`us-${r.ticker.toLowerCase()}`, r.ticker, r.ticker);
            db.prepare(`
                INSERT INTO intelligence_event VALUES (
                    ?, ?, ?, 'RESEARCH_IMPORT', ?, NULL, '2026-07-18T10:00:00Z',
                    'valuation', 1.0, 'ACTIVE', ?, ?, NULL, NULL, ?, ?
                )
            `).run(
                `event-${i}`, i + 1, `us-${r.ticker.toLowerCase()}`, r.effectiveAt,
                `${r.ticker} Research`, r.body, `key-${i}`, `hash-${i}`
            );
        });
        db.close();
    }

    beforeEach(() => {
        for (const p of [tempDbPath]) if (fs.existsSync(p)) fs.unlinkSync(p);
        fs.rmSync(tempResearchDir, { recursive: true, force: true });
        fs.mkdirSync(tempResearchDir, { recursive: true });
    });

    afterEach(() => {
        if (fs.existsSync(tempDbPath)) fs.unlinkSync(tempDbPath);
        fs.rmSync(tempResearchDir, { recursive: true, force: true });
    });

    it('rejects a filename matching neither shape', async () => {
        seedDb([]);
        const result = await getResearchReport('not-a-valid-name.txt', tempDbPath, tempResearchDir);
        expect(result).to.deep.equal({ kind: 'invalid' });
    });

    it('serves a dated filename found in the ledger', async () => {
        seedDb([{ ticker: 'MSFT', effectiveAt: '2026-07-18', body: 'Microsoft is growing' }]);
        const result = await getResearchReport('MSFT_2026-07-18.md', tempDbPath, tempResearchDir);
        expect(result).to.deep.equal({
            kind: 'found',
            filename: 'MSFT_2026-07-18.md',
            content: 'Microsoft is growing',
            ticker: 'MSFT',
            date: '2026-07-18',
        });
    });

    it('returns not_found for a dated filename missing from the ledger, even when a stale file of the same name exists on disk (no fs fallback)', async () => {
        seedDb([]); // ledger has no matching row
        fs.writeFileSync(
            path.join(tempResearchDir, 'MSFT_2026-07-18.md'),
            'STALE FS CONTENT — must never be served'
        );
        const result = await getResearchReport('MSFT_2026-07-18.md', tempDbPath, tempResearchDir);
        expect(result).to.deep.equal({ kind: 'not_found' });
    });

    it('serves a canonical (.summary.md) filename from disk — unaffected by ledger state', async () => {
        seedDb([]);
        fs.writeFileSync(path.join(tempResearchDir, 'PLTR.summary.md'), 'Palantir summary body');
        const result = await getResearchReport('PLTR.summary.md', tempDbPath, tempResearchDir);
        expect(result).to.deep.equal({
            kind: 'found',
            filename: 'PLTR.summary.md',
            content: 'Palantir summary body',
            ticker: 'PLTR',
            date: null,
        });
    });

    it('returns not_found for a canonical filename missing from disk', async () => {
        seedDb([]);
        const result = await getResearchReport('NVDA.timeline.md', tempDbPath, tempResearchDir);
        expect(result).to.deep.equal({ kind: 'not_found' });
    });
});

