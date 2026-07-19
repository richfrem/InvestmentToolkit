/**
 * ProjectionService.ts - DCF Projections persistence and lifecycle manager.
 *
 * Purpose:
 *   Manages the lifecycle of DCF projections, including validation, versioning, and
 *   SQLite persistence (ADR-029). Delegates all storage to `ProjectionRepository`, which
 *   reads/writes the shared `domain_model.sqlite` `projection_version`/
 *   `projection_scenario` tables via `better-sqlite3`.
 *
 * Layer:
 *   Backend / Services / Data Persistence
 *
 * Usage Examples:
 *   await projectionService.saveProjection(projectionData);
 *   const list = await projectionService.getProjections('AAPL');
 *
 * Migration note (Task 5, replaces the prior fs.promises + proper-lockfile
 * implementation that wrote `data/projections/{TICKER}.json`):
 *   `proper-lockfile` is no longer used in this file. It existed solely to serialize
 *   concurrent read-modify-write cycles against the ticker's JSON file. SQLite (via
 *   better-sqlite3's synchronous, single-connection API and `db.transaction()`) makes
 *   each upsert atomic at the statement/transaction level, so the same class of race this
 *   file's lock protected against can no longer occur here. `proper-lockfile` remains a
 *   dependency and is still used elsewhere in the codebase — this note only concerns this
 *   file.
 *
 * Key Functions (Index):
 *   - getProjections(ticker: string) - Retrieves all stored projection versions for a specific ticker symbol
 *   - getAllProjections() - Aggregates projections across all tickers for portfolio-wide analysis
 *   - saveProjection(projection: Projection) - Validates incoming data, manages version increments, and performs atomic writes
 *   - deleteProjection(ticker: string, id: string) - Locates and deletes a specific projection version
 *
 * Key Input Dependencies:
 *   - ./ProjectionRepository (SQLite read/write against data/domain_model.sqlite)
 *   - ../utils/zod-schemas (Projection, ProjectionSchema validation)
 *
 * Key Output Dependencies:
 *   - investment_screener/backend/data/domain_model.sqlite (writes projection_version / projection_scenario rows)
 */
import { Projection, ProjectionSchema } from '../utils/zod-schemas';
import { ProjectionRepository } from './ProjectionRepository';
import { DOMAIN_MODEL_DB_FILE } from '../utils/paths';

export class ProjectionService {
    private repository: ProjectionRepository;

    constructor(dbPath: string = DOMAIN_MODEL_DB_FILE) {
        this.repository = new ProjectionRepository(dbPath);
    }

    async getProjections(ticker: string): Promise<Projection[]> {
        try {
            return this.repository.findByTicker(ticker);
        } catch (error) {
            console.error(`[ProjectionService] Error reading projections for ${ticker}:`, error);
            return [];
        }
    }

    async getAllProjections(): Promise<Projection[]> {
        return this.repository.findAll();
    }

    async saveProjection(projection: Projection): Promise<void> {
        // 1. Zod Validation — use parseResult.data so .passthrough() fields (analyticsLog,
        //    scenario year5/risks fields, etc.) are included in the object we save.
        const parseResult = ProjectionSchema.safeParse(projection);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }
        const validated = parseResult.data as Projection;

        // Upsert-by-id-then-version-increment (conflict/version logic lives in the
        // repository so it can be exercised directly against a real SQLite file in tests).
        this.repository.upsertProjection(validated);
    }

    async deleteProjection(ticker: string, id: string): Promise<boolean> {
        return this.repository.deleteById(ticker, id);
    }
}

export const projectionService = new ProjectionService();
