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
 * Schema ownership (Python owns it):
 *   This class creates and alters NO tables. The schema is the numbered SQL files in
 *   `backend/schema/domain_model/`, applied by `py_services/domain_model/schema_migrator.py`.
 *   `ensureSchema()` below only verifies `PRAGMA user_version` through
 *   `utils/schemaVersion.ts` (a brand-new empty file is built by asking the Python
 *   migrator; a populated file that is behind or ahead is refused with a message).
 *   To change a table, add the next migration file. Never add DDL here.
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
 *   A re-save of the same `id` keeps the stale-version conflict check against that
 *   id's latest row, but also takes `MAX(version) + 1` for the ticker, so it can
 *   never land on (and ON CONFLICT-overwrite) an existing row of any identity.
 *
 * Key Functions (Index):
 *   - projectionMetadata(row) - Normalize Python snapshot fields and rate units for the API
 *   - rowToProjection(row) - Restore saved scenarios and metadata into the shared API contract
 *   - findByTicker(ticker) - Current-state-per-identity rows for one ticker (MAX version
 *     per distinct `legacy_id`/synthetic identity — see Finding 2 fix note), version-ascending
 *   - findAll() - Current-state-per-identity rows across all tickers
 *   - upsertProjection(validated) - Upsert-by-id-then-version-increment (see above)
 *   - deleteById(ticker, id) - Delete one projection row + its scenarios, returns found/not-found
 */
import Database from 'better-sqlite3';
import crypto from 'crypto';
import { Projection, ProjectionSchema } from '../utils/zod-schemas';
import { ensureSchemaReady } from '../utils/schemaVersion';

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
        this.ensureSchema(dbPath);
    }

    close(): void {
        this.db.close();
    }

    /** Connection settings only. The schema itself is owned by Python (see
     * `utils/schemaVersion.ts`): this verifies the version and never creates or
     * alters a table. */
    private ensureSchema(dbPath: string): void {
        this.db.pragma('journal_mode = WAL');
        this.db.pragma('foreign_keys = ON');
        ensureSchemaReady(this.db, dbPath);
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

    /** Normalize the canonical Python snapshot and discount settings once at the API boundary. */
    private projectionMetadata(row: ProjectionVersionRow) {
        const saved = row.snapshot_json ? JSON.parse(row.snapshot_json) : {};
        const analyticsLog = row.analytics_log_json ? JSON.parse(row.analytics_log_json) : undefined;
        // Structured Python persistence uses decimals; raw API JSON uses percent
        // and bypasses this reconstruction. Never infer units from rate magnitude.
        const rate = analyticsLog?.valuationModel?.discountRateAudit?.selectedRate
            ?? saved.discountRate ?? analyticsLog?.wacc;
        return {
            snapshot: {
                ...saved,
                price: saved.price ?? saved.currentPrice,
                revenue: saved.revenue ?? saved.baseRevenue,
                shares: saved.shares ?? saved.baseShares,
                currency: saved.currency ?? 'USD',
                lastActualPS: saved.lastActualPS ?? null,
            },
            globalSettings: {
                discountRate: rate == null ? undefined : rate * 100,
                timeHorizon: saved.horizon ?? 5,
            },
            analyticsLog,
        };
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

        const { snapshot, analyticsLog, globalSettings } = this.projectionMetadata(row);

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
            globalSettings,
            analyticsLog,
        };

        if (row.fair_value !== null || row.action !== null) {
            reconstructed.aiThesis = {
                model: row.model ?? 'unknown',
                rationale: row.rationale ?? '',
                fairValue: row.fair_value ?? 0,
                action: row.action ?? 'HOLD',
                analyzedAt: row.analyzed_at ?? row.saved_at,
                researchReport: snapshot.researchReport ?? undefined,
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

    /** Upper-cased symbols of every investment that has at least one saved projection. */
    listProjectedTickers(): string[] {
        const rows = this.db
            .prepare(
                'SELECT DISTINCT i.symbol AS symbol FROM projection_version pv ' +
                'JOIN investment i ON i.investment_id = pv.investment_id ORDER BY i.symbol'
            )
            .all() as Array<{ symbol: string }>;
        return rows.map(r => r.symbol.toUpperCase());
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

        // Latest row for this id (ORDER BY is required: an id accumulates one row
        // per save, and an unordered lookup returned an older row).
        const existing = this.db
            .prepare('SELECT * FROM projection_version WHERE investment_id = ? AND legacy_id = ? ORDER BY version DESC LIMIT 1')
            .get(investmentId, validated.id) as ProjectionVersionRow | undefined;

        const final: any = { ...validated };

        if (existing) {
            if (existing.version > validated.version) {
                throw new Error(
                    `Conflict: Server has version ${existing.version}, incoming is ${validated.version}`
                );
            }
            final.updatedAt = new Date().toISOString();
        }
        // Always the next free slot for the ticker, never existing.version + 1:
        // another identity may already hold that slot, and ON CONFLICT DO UPDATE
        // below would silently replace it (APLD 2026-09-22 row, lost 2026-09-28).
        const maxRow = this.db
            .prepare('SELECT MAX(version) as maxVersion FROM projection_version WHERE investment_id = ?')
            .get(investmentId) as { maxVersion: number | null };
        const newVersion = maxRow.maxVersion ? maxRow.maxVersion + 1 : 1;
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
