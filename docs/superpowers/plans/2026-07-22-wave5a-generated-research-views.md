# Wave 5A — Generated Research Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the last piece of ADR-029's root-cause debt in the research-report domain: remove
the dead legacy-filesystem fallback branch in `docs.ts`'s `GET /api/research/:filename` route so
dated research reports are served from `intelligence_event` unconditionally, with no silent
fallback to a file that (confirmed below) no longer exists on disk.

**Architecture:** Extract the route's branching logic into a new exported, directly-testable
function `getResearchReport(filename, dbPath?, researchDir?)` in `docs.ts`, following this
codebase's established pattern (`getScreenerPositionsFromDb`, `queryLatestResearchFromLedger`) of
testing route logic as a plain function rather than through Express/supertest. The Express handler
becomes a thin wrapper that maps the function's result to an HTTP status.

**Tech Stack:** TypeScript/Express (`investment_screener/backend`), Mocha/Chai + `better-sqlite3`
for tests (matches `docs.research.spec.ts`'s existing test harness).

## Global Constraints

(Copied verbatim from the overall plan/spec — applies to this task.)

- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived. Table existence or data copying alone do not count.
- **No script opens its own SQLite connection outside the owning repository/service layer** — this
  task does not add one; it reuses the existing `query_ledger_research.py` bridge via
  `queryLatestResearchFromLedger`.
- **Every wave reports:** the Wave KPI table (JSON files before/after, files archived, reads/writes
  removed, producers/consumers migrated, remaining exceptions named).

## Pre-Implementation Findings (re-verified against real code/data on 2026-07-22, not copied from the plan's one-liner)

- Producer confirmed live: `plugins/stock-valuation/skills/stock-research/SKILL.md` already writes
  `RESEARCH_IMPORT` events via `python3 -m intelligence.event_store` — not a one-time migration
  script. No producer work needed this wave.
- Ledger confirmed populated: main checkout's `investment_screener/backend/data/intelligence.sqlite`
  has exactly 80 `RESEARCH_IMPORT` / `ACTIVE` rows (matches ADR-029's "80 research reports").
- **Fallback confirmed fully dead, not just redundant:** `ls investment_screener/backend/data/research/`
  matching the `TICKER_YYYY-MM-DD.md` (DATED) shape returns **zero files**. There is nothing left
  for the fs-fallback branch to ever successfully serve for a dated filename — it can only ever
  return a stale/wrong answer or fall through to 404 the slow way.
- **`.summary.md` / `.timeline.md` (CANONICAL shape) files are out of scope, correctly so:** these
  are `GENERATED_FROM_SQLITE` view files written by `py_services/intelligence/view_generator.py`
  (itself reading `intelligence_event`) — a legitimate render-to-disk cache, not dual-write debt.
  `query_ledger_research.py`'s `--get` only ever matches the DATED regex and returns `null`
  immediately for any CANONICAL filename, so today's ledger-then-fallback branch never actually
  serves CANONICAL files from the ledger — it always falls to fs for them. This plan preserves
  that fs read for CANONICAL filenames unchanged; only the DATED path's fallback is removed.
- **The route's 403 path-traversal branch is unreachable, confirmed by inspection:** both
  `DATED_FILENAME_RE` and `CANONICAL_FILENAME_RE` are closed character classes
  (`[A-Z0-9.-]{1,10}`) with no `/` or `..` possible — a filename that fails both regexes is
  already rejected as 400 before the path-join ever runs. This plan drops the dead check rather
  than carry it forward, consistent with this wave's purpose (removing debt that can't fire on
  real input, same category as the fs fallback itself).
- No new test infra needed: `docs.research.spec.ts` already has a `better-sqlite3`-backed
  temp-DB pattern (`tempDbPath`) to extend for the new function's tests.

---

### Task 1: Extract `getResearchReport()` and remove the dead fs-fallback branch

**Files:**
- Modify: `investment_screener/backend/src/routes/docs.ts:57-88` (the `GET /research/:filename`
  handler)
- Modify: `investment_screener/backend/tests/api/docs.research.spec.ts` (add new test block)

**Interfaces:**
- Produces: `getResearchReport(filename: string, dbPath?: string, researchDir?: string): Promise<ResearchReportResult>`
  where
  ```ts
  export type ResearchReportResult =
    | { kind: 'invalid' }
    | { kind: 'not_found' }
    | { kind: 'found'; filename: string; content: string; ticker: string; date: string | null };
  ```
- Consumes: existing `DATED_FILENAME_RE`, `CANONICAL_FILENAME_RE`, `parseResearchFilename`,
  `queryLatestResearchFromLedger(filename, dbPath?)` — all already defined in `docs.ts`, signatures
  unchanged.

- [ ] **Step 1: Write the failing tests**

Add this block to the end of `investment_screener/backend/tests/api/docs.research.spec.ts` (after
the existing `describe('docs.ts ledger query helpers', ...)` block, before the final blank line):

```ts
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm run test -w backend -- --grep "getResearchReport"` (from `investment_screener/`)

Expected: FAIL — `getResearchReport` is not exported from `../../src/routes/docs` (TypeScript
compile error / import failure).

- [ ] **Step 3: Implement `getResearchReport()` and rewire the route handler**

Replace lines 57-88 of `investment_screener/backend/src/routes/docs.ts` (the current
`router.get('/research/:filename', ...)` block) with:

```ts
export type ResearchReportResult =
    | { kind: 'invalid' }
    | { kind: 'not_found' }
    | { kind: 'found'; filename: string; content: string; ticker: string; date: string | null };

export async function getResearchReport(
    filename: string,
    dbPath?: string,
    researchDir: string = RESEARCH_DIR
): Promise<ResearchReportResult> {
    const isDated = DATED_FILENAME_RE.test(filename);
    const isCanonical = CANONICAL_FILENAME_RE.test(filename);
    if (!isDated && !isCanonical) {
        return { kind: 'invalid' };
    }

    if (isDated) {
        // Dated research reports live exclusively in intelligence_event (ADR-029 Wave 5A) —
        // no fs fallback. The legacy TICKER_YYYY-MM-DD.md files this used to fall back to no
        // longer exist on disk (confirmed 2026-07-22, 0 remaining).
        const report = await queryLatestResearchFromLedger(filename, dbPath);
        return report ? { kind: 'found', ...report } : { kind: 'not_found' };
    }

    // Canonical (.summary.md / .timeline.md) files are GENERATED_FROM_SQLITE render-to-disk
    // views (py_services/intelligence/view_generator.py), not stored in intelligence_event —
    // reading them from disk is the correct, current architecture, unchanged by this wave.
    const filepath = path.join(researchDir, filename);
    try {
        const content = await fs.promises.readFile(filepath, 'utf-8');
        const { ticker, date } = parseResearchFilename(filename);
        return { kind: 'found', filename, content, ticker, date };
    } catch (err: any) {
        if (err.code === 'ENOENT') return { kind: 'not_found' };
        throw err;
    }
}

router.get('/research/:filename', async (req, res) => {
    try {
        const result = await getResearchReport(req.params.filename);
        if (result.kind === 'invalid') {
            res.status(400).json({ error: 'Invalid filename format. Expected: TICKER_YYYY-MM-DD.md' });
            return;
        }
        if (result.kind === 'not_found') {
            res.status(404).json({ error: 'Research report not found' });
            return;
        }
        res.json({ filename: result.filename, content: result.content, ticker: result.ticker, date: result.date });
    } catch (err: any) {
        console.error(`[API] Error reading research report:`, err);
        res.status(500).json({ error: 'Failed to read research report' });
    }
});
```

Also update the file-header comment block (lines 1-33) to remove any implication of an fs
fallback for dated filenames — adjust the `Routes Index` line for `GET /research/:filename` to:
`Fetches a specific research report (dated filenames: intelligence_event only, no fs fallback;
canonical .summary/.timeline filenames: generated view files on disk)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm run test -w backend -- --grep "getResearchReport|DATED_FILENAME_RE|ledger query helpers"`
(from `investment_screener/`)

Expected: PASS, all cases including the pre-existing `docs.ts ledger query helpers` and
`DATED_FILENAME_RE / CANONICAL_FILENAME_RE` describe blocks (unchanged, must still pass).

- [ ] **Step 5: Run the full backend test suite to confirm no regressions**

Run: `npm run test -w backend` (from `investment_screener/`)

Expected: same pass/fail baseline as before this change — the two pre-existing known-unrelated
failures (`zod-schemas.spec.ts`, the `InvestmentRepository` real-sqlite parity test) may still
fail; no *new* failures.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/src/routes/docs.ts investment_screener/backend/tests/api/docs.research.spec.ts
git commit -m "fix(docs.ts): remove dead fs-fallback for dated research reports (ADR-029/Wave 5A)"
```

---

## Wave KPI Table (fill in at wave exit)

| Metric | Before | After |
|---|---|---|
| JSON/JSONL files in this domain | 0 (already ledger-backed; this was a code-path issue, not a file-migration one) | 0 |
| Dead fallback branches removed | 1 (fs fallback for dated filenames) | 0 |
| Producers on SQLite | 1 (`stock-research` skill, already live) | 1 (unchanged) |
| Consumers on SQLite (unconditional, no fallback) | 0 (conditional w/ fallback) | 1 (`GET /research/:filename`, dated path) |
| Real fs reads remaining (by design) | CANONICAL view files | CANONICAL view files (unchanged, correct) |

## Definition of Done for This Wave

- [ ] `getResearchReport` exported and unit-tested per Task 1.
- [ ] No fs-fallback code path remains reachable for DATED filenames.
- [ ] Full backend test suite run with no new failures vs. documented baseline.
- [ ] Wave exit report + handoff written per the kickoff prompt's Way of Working §4.
- [ ] PR opened to `main`, not merged by the agent.
