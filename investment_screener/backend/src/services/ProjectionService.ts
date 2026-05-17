/**
 * ProjectionService.ts (TypeScript Service)
 * =====================================
 *
 * Purpose:
 *     Manages the lifecycle of DCF projections, including validation, versioning, and file-system persistence.
 *     Implements atomic writes and file locking to ensure data integrity during concurrent edits.
 *
 * Layer: Backend / Services / Data Persistence
 *
 * Usage Examples:
 *     await projectionService.saveProjection(projectionData);
 *     const list = await projectionService.getProjections('AAPL');
 *
 * Key Functions:
 *     - saveProjection() - Validates incoming data against Zod schemas, manages version increments, and performs atomic writes
 *     - getProjections() - Retrieves all stored projection versions for a specific ticker symbol
 *     - getAllProjections() - Aggregates projections across all tickers for portfolio-wide analysis
 */
import fs from 'fs';
import path from 'path';
import { lock } from 'proper-lockfile';
import { Projection, ProjectionSchema } from '../utils/zod-schemas';
const PROJECTIONS_DIR = path.resolve(__dirname, '../../data/projections');

// Ensure directory exists
if (!fs.existsSync(PROJECTIONS_DIR)) {
    fs.mkdirSync(PROJECTIONS_DIR, { recursive: true });
}

export class ProjectionService {

    private getFilePath(ticker: string): string {
        // Sanitize ticker to prevent path traversal
        const safeTicker = ticker.replace(/[^A-Z0-9.\-]/g, '');
        return path.join(PROJECTIONS_DIR, `${safeTicker}.json`);
    }

    async getProjections(ticker: string): Promise<Projection[]> {
        const filePath = this.getFilePath(ticker);
        if (!fs.existsSync(filePath)) {
            return [];
        }
        try {
            const data = await fs.promises.readFile(filePath, 'utf-8');
            const json = JSON.parse(data);
            return Array.isArray(json) ? json : [];
        } catch (error) {
            console.error(`[ProjectionService] Error reading file for ${ticker}:`, error);
            return [];
        }
    }

    async getAllProjections(): Promise<Projection[]> {
        const files = (await fs.promises.readdir(PROJECTIONS_DIR)).filter(f => f.endsWith('.json'));
        let all: Projection[] = [];
        
        // Use Promise.all to read files in parallel for better performance
        const results = await Promise.all(files.map(async (f) => {
            try {
                const data = await fs.promises.readFile(path.join(PROJECTIONS_DIR, f), 'utf-8');
                return JSON.parse(data);
            } catch (e) {
                console.error(`[ProjectionService] Error loading ${f}`, e);
                return null;
            }
        }));

        for (const json of results) {
            if (Array.isArray(json)) all.push(...json);
        }
        return all;
    }

    async saveProjection(projection: Projection): Promise<void> {
        // 1. Zod Validation — use parseResult.data so .passthrough() fields (analyticsLog,
        //    scenario year5/risks fields, etc.) are included in the object we save.
        const parseResult = ProjectionSchema.safeParse(projection);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }
        const validated = parseResult.data as Projection;

        const ticker = validated.ticker;
        const filePath = this.getFilePath(ticker);

        if (!fs.existsSync(filePath)) {
            await fs.promises.writeFile(filePath, '[]');
        }

        let release: () => Promise<void>;
        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire file lock for saving.');
        }

        try {
            const fileContent = await fs.promises.readFile(filePath, 'utf-8');
            let projections: Projection[] = [];
            try {
                projections = JSON.parse(fileContent);
            } catch (e) {
                projections = [];
            }

            const existingIndex = projections.findIndex(p => p.id === validated.id);
            if (existingIndex !== -1) {
                const existing = projections[existingIndex];
                if (existing.version > validated.version) {
                    throw new Error(
                        `Conflict: Server has version ${existing.version}, incoming is ${validated.version}`
                    );
                }
                // Server-side increment
                (validated as any).version = existing.version + 1;
                (validated as any).updatedAt = new Date().toISOString();
                projections[existingIndex] = validated;
            } else {
                // New projection
                (validated as any).version = 1;
                projections.push(validated);
            }

            // Atomic write
            const tempPath = `${filePath}.tmp`;
            await fs.promises.writeFile(tempPath, JSON.stringify(projections, null, 2));
            await fs.promises.rename(tempPath, filePath);
        } finally {
            await release();
        }
    }

    async deleteProjection(ticker: string, id: string): Promise<boolean> {
        const filePath = this.getFilePath(ticker);
        if (!fs.existsSync(filePath)) return false;

        let release: () => Promise<void>;
        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire lock for deletion.');
        }

        try {
            const fileContent = await fs.promises.readFile(filePath, 'utf-8');
            let projections: Projection[] = JSON.parse(fileContent);

            const initialLength = projections.length;
            projections = projections.filter(p => p.id !== id);

            if (projections.length !== initialLength) {
                const tempPath = `${filePath}.tmp`;
                await fs.promises.writeFile(tempPath, JSON.stringify(projections, null, 2));
                await fs.promises.rename(tempPath, filePath);
                return true;
            }
            return false;

        } finally {
            await release();
        }
    }
}

export const projectionService = new ProjectionService();
