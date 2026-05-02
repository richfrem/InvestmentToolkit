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
            const data = fs.readFileSync(filePath, 'utf-8');
            const json = JSON.parse(data);
            return Array.isArray(json) ? json : [];
        } catch (error) {
            console.error(`[ProjectionService] Error reading file for ${ticker}:`, error);
            return [];
        }
    }

    async getAllProjections(): Promise<Projection[]> {
        const files = fs.readdirSync(PROJECTIONS_DIR).filter(f => f.endsWith('.json'));
        let all: Projection[] = [];
        for (const f of files) {
            try {
                const data = fs.readFileSync(path.join(PROJECTIONS_DIR, f), 'utf-8');
                const json = JSON.parse(data);
                if (Array.isArray(json)) all.push(...json);
            } catch (e) {
                console.error(`[ProjectionService] Error loading ${f}`, e);
            }
        }
        return all;
    }

    async saveProjection(projection: Projection): Promise<void> {
        // 1. Zod Validation
        const parseResult = ProjectionSchema.safeParse(projection);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }

        const ticker = projection.ticker;
        const filePath = this.getFilePath(ticker);

        if (!fs.existsSync(filePath)) {
            fs.writeFileSync(filePath, '[]');
        }

        let release: () => Promise<void>;
        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire file lock for saving.');
        }

        try {
            const fileContent = fs.readFileSync(filePath, 'utf-8');
            let projections: Projection[] = [];
            try {
                projections = JSON.parse(fileContent);
            } catch (e) {
                projections = [];
            }

            const existingIndex = projections.findIndex(p => p.id === projection.id);
            if (existingIndex !== -1) {
                const existing = projections[existingIndex];
                if (existing.version > projection.version) {
                    throw new Error(
                        `Conflict: Server has version ${existing.version}, incoming is ${projection.version}`
                    );
                }
                // Server-side increment
                projection.version = existing.version + 1;
                projection.updatedAt = new Date().toISOString();
                projections[existingIndex] = projection;
            } else {
                // New projection
                projection.version = 1;
                projections.push(projection);
            }

            // Atomic write
            const tempPath = `${filePath}.tmp`;
            fs.writeFileSync(tempPath, JSON.stringify(projections, null, 2));
            fs.renameSync(tempPath, filePath);
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
            const fileContent = fs.readFileSync(filePath, 'utf-8');
            let projections: Projection[] = JSON.parse(fileContent);

            const initialLength = projections.length;
            projections = projections.filter(p => p.id !== id);

            if (projections.length !== initialLength) {
                const tempPath = `${filePath}.tmp`;
                fs.writeFileSync(tempPath, JSON.stringify(projections, null, 2));
                fs.renameSync(tempPath, filePath);
                return true;
            }
            return false;

        } finally {
            await release();
        }
    }
}

export const projectionService = new ProjectionService();
