/**
 * ProjectionRepository.ts - SQLite persistence for DCF projection versions.
 *
 * Purpose:
 *   Reads and writes the shared `projection_version` / `projection_scenario` tables in
 *   `data/domain_model.sqlite` (ADR-029) via `better-sqlite3`. This is the same physical
 *   SQLite file the Python side writes/reads via
 *   `py_services/domain_model/{db_client,projection_repository,investment_repository}.py`
 *   — WAL mode is enabled so both processes can access it concurrently.
 *
 * Layer:
 *   Backend / Services / Data Persistence (SQLite-backed repository)
 *
 * Schema-shape contract (must stay in sync with `py_services/domain_model/db_client.py`):
 *   `ensureSchema()` below intentionally transcribes the SAME `CREATE TABLE IF NOT EXISTS`
 *   statements as `db_client.py::initialize_db` for `investment`, `strategy_pillar`,
 *   `sub_strategy`, `projection_version`, and `projection_scenario` (idempotent no-ops
 *   against the real, already-initialized file; load-bearing for fresh temp/`:memory:`
 *   test databases that have no schema yet). Do not invent a parallel/divergent schema.
 *   Python (`db_client.py`) is the single source of truth for this shared schema —
 *   `ensureSchema()` below must ONLY ever run `CREATE TABLE IF NOT EXISTS` /
 *   `CREATE INDEX IF NOT EXISTS` matching that file's DDL verbatim, column-for-column,
 *   including `raw_json`/`legacy_id` on `projection_version` (see below). It must NEVER
 *   run `ALTER TABLE` against the shared file as a side effect of construction — an
 *   earlier version of this file did exactly that (unconditional `ALTER TABLE
 *   projection_version ADD COLUMN ...` in the constructor), which silently mutated the
 *   real production `domain_model.sqlite` the moment anything imported this module,
 *   before `db_client.py` even knew those columns existed. Fixed in the Task 5 review
 *   pass: `db_client.py::initialize_db` now declares `raw_json`/`legacy_id` directly in
 *   its own `CREATE TABLE IF NOT EXISTS projection_version` DDL, and this file's
 *   `ensureSchema()` mirrors that DDL as a plain (no-op-if-already-there) `CREATE TABLE
 *   IF NOT EXISTS`, not a runtime schema migration.
 *
 * Round-trip fidelity design decision (`raw_json` / `legacy_id` columns):
 *   The Python schema's `projection_version` table (Task 1/4) has no column for the
 *   original Zod `Projection.id` (a UUID) nor a column holding the full validated object
 *   — `snapshot_json`/`analytics_log_json` hold only the `snapshot`/`analyticsLog`
 *   sub-objects, not `id`, `schemaVersion`, `name`, `dataPreferences`, `globalSettings`,
 *   or full `scenarios` (year5Shares etc. beyond the columns `projection_scenario`
 *   models). Task 4's real migration (see `migrate_projections_to_sqlite.py`) confirms
 *   this: it never passes `id` to `save_projection_version` at all. To satisfy this
 *   task's "full round-trip fidelity through `.passthrough()`" requirement for anything
 *   written through THIS repository, two nullable columns are added:
 *     - `legacy_id` TEXT — the original `Projection.id` (UUID), used to replicate
 *       `saveProjection`'s `projections.findIndex(p => p.id === validated.id)` lookup.
 *     - `raw_json` TEXT — the complete validated `Projection` object (post
 *       `ProjectionSchema.safeParse`, including all `.passthrough()` fields), the
 *       single source of truth `getProjections`/`getAllProjections` read from when
 *       present.
 *   Rows already migrated by Task 4 (115 real rows) have neither column populated —
 *   reads for those rows fall back to reconstructing a best-effort `Projection` shape
 *   from the structured columns + `projection_scenario` joins, with a deterministic
 *   synthetic UUID standing in for the missing `id` (see `deterministicUuid`). This is a
 *   known, pre-existing lossiness inherited from Task 4's column mapping, not introduced
 *   by this task — flagged in task-5-report.md.
 *
 * Version-slot collision safety:
 *   `projection_version` is uniquely keyed on `(investment_id, version)`. The original
 *   JSON-file model allowed multiple *independent* projection identities (`id`s) per
 *   ticker, each starting its own version count at 1 — two distinct `id`s for the same
 *   ticker could both be "version 1". That can't be represented in the SQL table's grain
 *   without a collision. `upsertProjection` avoids ever silently overwriting a
 *   different `id`'s row: a brand-new `id` for a ticker that already has other rows is
 *   assigned `version = MAX(existing versions for that ticker) + 1`, not a reset to 1.
 *   The exact "same `id` -> existing.version + 1, with a conflict check" rule is
 *   preserved unchanged for the common case (same `id` being re-saved).
 *
 * Key Functions (Index):
 *   - findByTicker(ticker) - Current-state-per-identity rows for one ticker (MAX version
 *     per distinct `legacy_id`/synthetic identity — see Finding 2 fix note), version-ascending
 *   - findAll() - Current-state-per-identity rows across all tickers
 *   - upsertProjection(validated) - Upsert-by-id-then-version-increment (see above)
 *   - deleteById(ticker, id) - Delete one projection row + its scenarios, returns found/not-found
 */
import Database from 'better-sqlite3';
import crypto from 'crypto';
import { Projection, ProjectionSchema } from '../utils/zod-schemas';

interface ProjectionVersionRow {
    projection_id: string;
    investment_id: string;
    version: number;
    saved_at: string;
    analyzed_at: string | null;
    model: string | null;
    fair_value: number | null;
    action: string | null;
    rationale: string | null;
    research_event_id: string | null;
    snapshot_json: string | null;
    analytics_log_json: string | null;
    raw_json: string | null;
    legacy_id: string | null;
    source?: string | null;
}

interface ProjectionScenarioRow {
    scenario_id: string;
    projection_id: string;
    scenario_name: string;
    weight: number | null;
    growth_rate: number | null;
    net_margin: number | null;
    exit_pe: number | null;
    quality_multiplier: number | null;
    share_change: number | null;
    rationale: string | null;
    moat_score: number | null;
    management_score: number | null;
    year5_revenue: number | null;
    year5_net_income: number | null;
    year5_eps: number | null;
    scenario_price: number | null;
    risks_json: string | null;
}

/** Deterministic, format-valid (RFC4122-looking) UUID derived from a stable seed string.
 * Used only as a synthetic `id` fallback for pre-existing rows that predate the
 * `legacy_id` column (Task 4's migrated data never stored the original `id`). */
function deterministicUuid(seed: string): string {
    const hash = crypto.createHash('sha256').update(seed).digest('hex');
    const chars = hash.slice(0, 32).split('');
    chars[12] = '4'; // version nibble
    const variantChars = ['8', '9', 'a', 'b'];
    chars[16] = variantChars[parseInt(chars[16], 16) % 4];
    const hex = chars.join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`;
}

export class ProjectionRepository {
    private db: Database.Database;

    constructor(dbPath: string) {
        this.db = new Database(dbPath);
        this.ensureSchema();
    }

    close(): void {
        this.db.close();
    }

    /** Transcribed from `py_services/domain_model/db_client.py::initialize_db` — see the
     * module-level comment above for the sync contract. Idempotent against the real,
     * already-initialized `domain_model.sqlite` file. */
    private ensureSchema(): void {
        this.db.pragma('journal_mode = WAL');
        this.db.pragma('foreign_keys = ON');

        this.db.exec(`
            CREATE TABLE IF NOT EXISTS strategy_pillar (
                pillar_id       TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                target_weight   REAL
            );

            CREATE TABLE IF NOT EXISTS sub_strategy (
                sub_strategy_id TEXT PRIMARY KEY,
                pillar_id       TEXT REFERENCES strategy_pillar(pillar_id),
                name            TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS investment (
                investment_id              TEXT PRIMARY KEY,
                symbol                      TEXT NOT NULL,
                name                        TEXT,
                asset_class                 TEXT NOT NULL,
                currency                    TEXT NOT NULL DEFAULT 'USD',
                lifecycle_status            TEXT,
                target_weight               REAL,
                target_action               TEXT,
                standing_decision_type      TEXT,
                standing_decision_reason    TEXT,
                standing_decision_source    TEXT,
                standing_decision_review    TEXT,
                pillar_id                   TEXT REFERENCES strategy_pillar(pillar_id),
                sub_strategy_id             TEXT REFERENCES sub_strategy(sub_strategy_id),
                thesis_for_inclusion        TEXT,
                agent_rationale             TEXT,
                is_watchlisted              INTEGER NOT NULL DEFAULT 0,
                watchlist_added_at          TEXT,
                latest_projection_id        TEXT REFERENCES projection_version(projection_id),
                latest_research_event_id    TEXT,
                thesis_breaker_status       TEXT,
                updated_at                  TEXT NOT NULL,
                UNIQUE(symbol)
            );

            CREATE TABLE IF NOT EXISTS projection_version (
                projection_id         TEXT PRIMARY KEY,
                investment_id         TEXT NOT NULL REFERENCES investment(investment_id),
                version               INTEGER NOT NULL,
                saved_at              TEXT NOT NULL,
                analyzed_at           TEXT,
                model                 TEXT,
                fair_value            REAL,
                action                TEXT,
                rationale             TEXT,
                research_event_id     TEXT,
                snapshot_json         TEXT,
                analytics_log_json    TEXT,
                raw_json              TEXT,
                legacy_id             TEXT,
                source                TEXT,
                UNIQUE(investment_id, version)
            );

            CREATE TABLE IF NOT EXISTS projection_scenario (
                scenario_id         TEXT PRIMARY KEY,
                projection_id       TEXT NOT NULL REFERENCES projection_version(projection_id),
                scenario_name       TEXT NOT NULL,
                weight              REAL,
                growth_rate         REAL,
                net_margin          REAL,
                exit_pe             REAL,
                quality_multiplier  REAL,
                share_change        REAL,
                rationale           TEXT,
                moat_score          INTEGER,
                management_score    INTEGER,
                year5_revenue       REAL,
                year5_net_income    REAL,
                year5_eps           REAL,
                scenario_price      REAL,
                risks_json          TEXT,
                UNIQUE(projection_id, scenario_name)
            );

            CREATE INDEX IF NOT EXISTS idx_projection_investment
                ON projection_version(investment_id);
            CREATE INDEX IF NOT EXISTS idx_projection_scenario_projection
                ON projection_scenario(projection_id);
        `);
    }

    /** Mirrors `investment_repository.py::resolve_investment` — idempotent lookup-or-insert
     * of the `investment` row for a symbol, returning its `investment_id`. */
    private resolveInvestmentId(ticker: string): string {
        const existing = this.db
            .prepare('SELECT investment_id FROM investment WHERE symbol = ?')
            .get(ticker) as { investment_id: string } | undefined;
        if (existing) return existing.investment_id;

        const investmentId = ticker.toUpperCase();
        const now = new Date().toISOString();
        this.db
            .prepare(
                `INSERT INTO investment (investment_id, symbol, name, asset_class, currency, updated_at)
                 VALUES (?, ?, ?, 'EQUITY', 'USD', ?)`
            )
            .run(investmentId, ticker, ticker, now);
        return investmentId;
    }

    /** Reconstructs a `Projection` object for one `projection_version` row. Uses
     * `raw_json` verbatim when present (full fidelity); otherwise best-effort-rebuilds
     * from the structured columns + a `projection_scenario` join (legacy migrated rows,
     * see module docstring for the known lossiness this implies). */
    private rowToProjection(row: ProjectionVersionRow): Projection {
        if (row.raw_json) {
            return JSON.parse(row.raw_json) as Projection;
        }

        const scenarioRows = this.db
            .prepare('SELECT * FROM projection_scenario WHERE projection_id = ?')
            .all(row.projection_id) as ProjectionScenarioRow[];

        const toScenario = (name: string) => {
            const s = scenarioRows.find(r => r.scenario_name === name);
            if (!s) return undefined;
            return {
                weight: s.weight ?? 0,
                growthRate: s.growth_rate ?? 0,
                netMargin: s.net_margin ?? 0,
                exitPE: s.exit_pe ?? 0,
                qualityMultiplier: s.quality_multiplier ?? 1,
                shareChange: s.share_change ?? 0,
                rationale: s.rationale ?? undefined,
                moatScore: s.moat_score ?? undefined,
                managementScore: s.management_score ?? undefined,
                year5Revenue: s.year5_revenue ?? undefined,
                year5NetIncome: s.year5_net_income ?? undefined,
                year5EPS: s.year5_eps ?? undefined,
                scenarioPrice: s.scenario_price ?? undefined,
                risks: s.risks_json ? JSON.parse(s.risks_json) : undefined,
            };
        };

        const snapshot = row.snapshot_json ? JSON.parse(row.snapshot_json) : {};
        const analyticsLog = row.analytics_log_json ? JSON.parse(row.analytics_log_json) : undefined;

        const reconstructed: any = {
            ticker: row.investment_id,
            id: row.legacy_id ?? deterministicUuid(row.projection_id),
            source: row.source ?? 'AI_AGENT',
            schemaVersion: '1.2',
            version: row.version,
            savedAt: row.saved_at,
            updatedAt: row.saved_at,
            name: `${row.investment_id} v${row.version}`,
            rationale: row.rationale ?? undefined,
            snapshot,
            dataPreferences: { growthBasis: 'ttm', marginBasis: 'ttm' },
            scenarios: {
                bear: toScenario('bear'),
                base: toScenario('base'),
                bull: toScenario('bull'),
            },
            globalSettings: { discountRate: 10, timeHorizon: 5 },
            analyticsLog,
        };

        if (row.fair_value !== null || row.action !== null) {
            reconstructed.aiThesis = {
                model: row.model ?? 'unknown',
                rationale: row.rationale ?? '',
                fairValue: row.fair_value ?? 0,
                action: row.action ?? 'HOLD',
                analyzedAt: row.analyzed_at ?? row.saved_at,
            };
        }

        // Validation gate (Task 5 review, Finding 3): a reconstructed legacy row
        // synthesizes placeholder values for required Zod fields (name, dataPreferences,
        // globalSettings, etc.) since the structured columns don't carry them. Never
        // serve a malformed reconstruction silently — run safeParse and log loudly (with
        // ticker/id) if it fails, matching this project's standing rule against silently
        // degraded data being served as if it were complete. We still return the
        // best-effort object even on failure: some legacy fields genuinely can't be
        // recovered, and callers historically tolerated this shape.
        const validation = ProjectionSchema.safeParse(reconstructed);
        if (!validation.success) {
            console.warn(
                `[ProjectionRepository] Reconstructed legacy projection failed schema validation ` +
                `(ticker=${row.investment_id}, id=${reconstructed.id}, projection_id=${row.projection_id}): ` +
                validation.error.message
            );
        }

        return reconstructed as Projection;
    }

    /** Groups `projection_version` rows by `(investment_id, identity)` — where
     * `identity` is `legacy_id` when present (all rows saved through `upsertProjection`
     * going forward), or the row's own `projection_id` when absent (pre-existing
     * migrated rows that predate the `legacy_id` column, each treated as its own
     * distinct identity — see module docstring) — and keeps only the MAX-`version` row
     * per group. Restores the old filesystem-JSON model's "array length = number of
     * distinct projection identities" semantics (Task 5 review, Finding 2): a ticker
     * re-saved under the same `id` N times must return ONE current-state entry, not N
     * stale version rows. */
    private static readonly CURRENT_PER_IDENTITY_SQL = `
        SELECT pv.* FROM projection_version pv
        INNER JOIN (
            SELECT investment_id,
                   COALESCE(legacy_id, projection_id) AS identity,
                   MAX(version) AS max_version
            FROM projection_version
            {WHERE_CLAUSE}
            GROUP BY investment_id, identity
        ) latest
            ON pv.investment_id = latest.investment_id
           AND COALESCE(pv.legacy_id, pv.projection_id) = latest.identity
           AND pv.version = latest.max_version
        ORDER BY pv.investment_id ASC, pv.version ASC
    `;

    findByTicker(ticker: string): Projection[] {
        const investment = this.db
            .prepare('SELECT investment_id FROM investment WHERE symbol = ?')
            .get(ticker) as { investment_id: string } | undefined;
        if (!investment) return [];

        const sql = ProjectionRepository.CURRENT_PER_IDENTITY_SQL.replace(
            '{WHERE_CLAUSE}',
            'WHERE investment_id = ?'
        );
        const rows = this.db.prepare(sql).all(investment.investment_id) as ProjectionVersionRow[];
        return rows.map(r => this.rowToProjection(r));
    }

    findAll(): Projection[] {
        const sql = ProjectionRepository.CURRENT_PER_IDENTITY_SQL.replace('{WHERE_CLAUSE}', '');
        const rows = this.db.prepare(sql).all() as ProjectionVersionRow[];
        return rows.map(r => this.rowToProjection(r));
    }

    /**
     * Upsert-by-id-then-version-increment, replicating `ProjectionService.saveProjection`'s
     * confirmed semantics exactly:
     *   - Look up an existing row for this ticker by `legacy_id === validated.id`.
     *   - If found and `existing.version > validated.version`: throw the same conflict
     *     error message the original file-backed implementation threw.
     *   - If found: `version = existing.version + 1`, `updatedAt = now`, replace in place.
     *   - If not found: this is a new projection identity for this ticker. `version = 1`
     *     UNLESS other rows already exist for this ticker (version-slot collision safety,
     *     see module docstring), in which case `version = MAX(existing) + 1`.
     * Returns the final persisted `Projection` (post version-increment).
     */
    upsertProjection(validated: Projection): Projection {
        const ticker = validated.ticker;
        const investmentId = this.resolveInvestmentId(ticker);

        const existing = this.db
            .prepare('SELECT * FROM projection_version WHERE investment_id = ? AND legacy_id = ?')
            .get(investmentId, validated.id) as ProjectionVersionRow | undefined;

        const final: any = { ...validated };

        let newVersion: number;
        if (existing) {
            if (existing.version > validated.version) {
                throw new Error(
                    `Conflict: Server has version ${existing.version}, incoming is ${validated.version}`
                );
            }
            newVersion = existing.version + 1;
            final.updatedAt = new Date().toISOString();
        } else {
            const maxRow = this.db
                .prepare('SELECT MAX(version) as maxVersion FROM projection_version WHERE investment_id = ?')
                .get(investmentId) as { maxVersion: number | null };
            newVersion = maxRow.maxVersion ? maxRow.maxVersion + 1 : 1;
        }
        final.version = newVersion;

        const projectionId = `${investmentId}:${newVersion}`;
        const snapshotJson = final.snapshot ? JSON.stringify(final.snapshot) : null;
        const analyticsLogJson = final.analyticsLog ? JSON.stringify(final.analyticsLog) : null;
        const fairValue = final.aiThesis?.fairValue ?? null;
        const action = final.aiThesis?.action ?? null;
        const analyzedAt = final.aiThesis?.analyzedAt ?? null;
        const model = final.aiThesis?.model ?? null;
        const rationale = final.rationale ?? null;
        const source = final.source ?? null;

        const upsert = this.db.transaction(() => {
            this.db
                .prepare(
                    `INSERT INTO projection_version
                        (projection_id, investment_id, version, saved_at, analyzed_at, model,
                         fair_value, action, rationale, snapshot_json, analytics_log_json,
                         raw_json, legacy_id, source)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                     ON CONFLICT(investment_id, version) DO UPDATE SET
                        saved_at=excluded.saved_at, analyzed_at=excluded.analyzed_at,
                        model=excluded.model, fair_value=excluded.fair_value,
                        action=excluded.action, rationale=excluded.rationale,
                        snapshot_json=excluded.snapshot_json,
                        analytics_log_json=excluded.analytics_log_json,
                        raw_json=excluded.raw_json, legacy_id=excluded.legacy_id,
                        source=excluded.source`
                )
                .run(
                    projectionId,
                    investmentId,
                    newVersion,
                    final.savedAt,
                    analyzedAt,
                    model,
                    fairValue,
                    action,
                    rationale,
                    snapshotJson,
                    analyticsLogJson,
                    JSON.stringify(final),
                    final.id,
                    source
                );

            const scenarios = final.scenarios ?? {};
            for (const scenarioName of ['bear', 'base', 'bull'] as const) {
                const s = scenarios[scenarioName];
                if (!s) continue;
                const scenarioId = `${projectionId}:${scenarioName}`;
                this.db
                    .prepare(
                        `INSERT INTO projection_scenario
                            (scenario_id, projection_id, scenario_name, weight, growth_rate,
                             net_margin, exit_pe, quality_multiplier, share_change, rationale,
                             moat_score, management_score, year5_revenue, year5_net_income,
                             year5_eps, scenario_price, risks_json)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                         ON CONFLICT(projection_id, scenario_name) DO UPDATE SET
                            weight=excluded.weight, growth_rate=excluded.growth_rate,
                            net_margin=excluded.net_margin, exit_pe=excluded.exit_pe,
                            quality_multiplier=excluded.quality_multiplier,
                            share_change=excluded.share_change, rationale=excluded.rationale,
                            moat_score=excluded.moat_score, management_score=excluded.management_score,
                            year5_revenue=excluded.year5_revenue, year5_net_income=excluded.year5_net_income,
                            year5_eps=excluded.year5_eps, scenario_price=excluded.scenario_price,
                            risks_json=excluded.risks_json`
                    )
                    .run(
                        scenarioId,
                        projectionId,
                        scenarioName,
                        s.weight ?? null,
                        s.growthRate ?? null,
                        s.netMargin ?? null,
                        s.exitPE ?? null,
                        s.qualityMultiplier ?? null,
                        s.shareChange ?? null,
                        s.rationale ?? null,
                        s.moatScore ?? null,
                        s.managementScore ?? null,
                        s.year5Revenue ?? null,
                        s.year5NetIncome ?? null,
                        s.year5EPS ?? null,
                        s.scenarioPrice ?? null,
                        s.risks ? JSON.stringify(s.risks) : null
                    );
            }
        });
        upsert();

        return final as Projection;
    }

    deleteById(ticker: string, id: string): boolean {
        const investment = this.db
            .prepare('SELECT investment_id FROM investment WHERE symbol = ?')
            .get(ticker) as { investment_id: string } | undefined;
        if (!investment) return false;

        const rows = this.db
            .prepare('SELECT * FROM projection_version WHERE investment_id = ?')
            .all(investment.investment_id) as ProjectionVersionRow[];

        const match = rows.find(
            r => (r.legacy_id ?? deterministicUuid(r.projection_id)) === id
        );
        if (!match) return false;

        const del = this.db.transaction(() => {
            this.db.prepare('DELETE FROM projection_scenario WHERE projection_id = ?').run(match.projection_id);
            this.db.prepare('DELETE FROM projection_version WHERE projection_id = ?').run(match.projection_id);
        });
        del();
        return true;
    }
}
