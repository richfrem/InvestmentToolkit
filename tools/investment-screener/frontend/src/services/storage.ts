
import {
    fetchProjections,
    saveProjection as apiSave,
    deleteProjection as apiDelete,
} from './api';
import type { Projection, Scenario } from './api';

// --- Legacy Interface (V1.0) ---
interface LegacyProjection {
    id: string;
    ticker: string;
    savedAt: string;
    name?: string;
    scenarios: {
        growthRate: number;
        netMargin: number;
        exitPE: number;
        qualityMultiplier: number;
        shareChange: number;
        discountRate: number;
        timeHorizon: number;
        terminalGrowth: number;
        aiThesis?: {
            rationale: string;
            fairValue: number;
            action: string;
        };
    };
}

const STORAGE_PREFIX = 'projections_';

/**
 * Migrates V1.0 flat projections to V1.1 multi-scenario schema.
 * Maps the single scenario to 'base' with 100% weight.
 */
const migrateV1toV1_1 = (legacy: LegacyProjection): Projection => {
    const baseScenario: Scenario = {
        weight: 1.0,
        growthRate: legacy.scenarios.growthRate,
        netMargin: legacy.scenarios.netMargin,
        exitPE: legacy.scenarios.exitPE,
        qualityMultiplier: legacy.scenarios.qualityMultiplier || 1.0,
        shareChange: legacy.scenarios.shareChange || 0,
        rationale: "Migrated from V1.0",
    };

    // Dummy scenario for bear/bull (weight 0)
    const zeroScenario: Scenario = { ...baseScenario, weight: 0 };

    return {
        ticker: legacy.ticker,
        id: legacy.id,
        schemaVersion: '1.1',
        version: 1,
        savedAt: legacy.savedAt,
        updatedAt: new Date().toISOString(),
        name: legacy.name || 'Untitled Projection',
        snapshot: {
            // Minimal snapshot since historical data is missing
            price: 0,
            currency: 'USD',
            shares: 0,
            revenue: 0,
            lastActualPS: 0
        },
        dataPreferences: {
            growthBasis: 'next', // Default
            marginBasis: 'next'
        },
        scenarios: {
            bear: zeroScenario,
            base: baseScenario,
            bull: zeroScenario
        },
        aiThesis: legacy.scenarios.aiThesis ? {
            model: "legacy",
            rationale: legacy.scenarios.aiThesis.rationale,
            fairValue: legacy.scenarios.aiThesis.fairValue,
            action: legacy.scenarios.aiThesis.action as 'BUY' | 'SELL' | 'HOLD',
            analyzedAt: legacy.savedAt
        } : undefined,
        globalSettings: {
            discountRate: legacy.scenarios.discountRate,
            timeHorizon: legacy.scenarios.timeHorizon
        }
    };
};

export const storage = {

    // API-First Sync Manager
    syncProjections: async (ticker: string): Promise<Projection[]> => {
        const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;

        // 1. Fetch from API (Source of Truth)
        const serverProjections = await fetchProjections(ticker);

        // 2. Load LocalStorage (Legacy or Cache)
        const localRaw = localStorage.getItem(key);
        let localProjections: any[] = localRaw ? JSON.parse(localRaw) : [];

        // Red Team C1 Fix: Handle Network Failure (serverProjections === null)
        if (serverProjections === null) {
            console.warn(`[Storage] API unreachable for ${ticker}, using local cache.`);
            // If we have V1.1 local data, return it (Offline Mode)
            if (localProjections.length > 0 && localProjections[0].schemaVersion === '1.1') {
                return localProjections;
            }
            // If local is empty or legacy, we can't do much. Return empty for now.
            return [];
        }

        // 3. Migration Check
        // If we have local data but it looks like V1 (no schemaVersion), migrate and push to server
        const needsMigration = localProjections.length > 0 && !localProjections[0].schemaVersion;

        if (needsMigration) {
            console.log(`[Storage] Migrating ${localProjections.length} V1 projections for ${ticker}...`);
            const migrated = localProjections.map(migrateV1toV1_1);

            // Push migrated data to server
            for (const p of migrated) {
                // Check if already on server to avoid duplicates? 
                // Simple check by ID.
                if (!serverProjections.find(sp => sp.id === p.id)) {
                    try {
                        await apiSave(p);
                        serverProjections.push(p); // Update our view of server data
                    } catch (e) {
                        console.error(`[Storage] Failed to sync migrated projection ${p.id}`, e);
                    }
                }
            }
            // Update local cache with the fully migrated/synced list
            localStorage.setItem(key, JSON.stringify(serverProjections));
            return serverProjections;
        }

        // 4. Standard Sync using Versioning
        // For now, simpler strategy: Server wins. 
        // We replace local cache with server data. 
        // (In a full offline-first app, we'd merge, but Red Team advised "API First")
        if (serverProjections.length > 0) {
            localStorage.setItem(key, JSON.stringify(serverProjections));
            return serverProjections;
        }

        // 5. Fallback: If server empty, return local V1.1 cache?
        // If server is empty but we have V1.1 local data, it means we might have unsynced changes?
        // Or server was wiped. 
        // Let's assume server is truth. If server 0, we show 0.
        // The null check at step 2 handles network errors.

        // Let's trust the server array if it was a success. 
        // Since `fetchProjections` returns [] on error, this might wipe local data if API is down.
        // IMPROVEMENT: `fetchProjections` should throw or return null on error.

        // Use local cache if it exists and looks valid (V1.1)
        if (localProjections.length > 0 && localProjections[0].schemaVersion === '1.1') {
            // If server returned empty, maybe we should try to push local?
            // For now, let's just return local cache if server is empty but local is not.
            return localProjections;
        }

        return [];
    },

    getProjections: (ticker: string): Projection[] => {
        try {
            const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;
            const data = localStorage.getItem(key);
            if (!data) return [];
            return JSON.parse(data);
        } catch (e) {
            console.error('Failed to load local projections:', e);
            return [];
        }
    },

    saveProjection: async (projection: Projection): Promise<void> => {
        const ticker = projection.ticker;
        try {
            // 1. API Write (Strict First)
            await apiSave(projection);

            // 2. Update Local Cache on Success
            const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;
            const existing = storage.getProjections(ticker);

            // Remove old version if exists, add new to top
            const updated = [projection, ...existing.filter(p => p.id !== projection.id)];
            localStorage.setItem(key, JSON.stringify(updated));

        } catch (e: any) {
            console.error('Failed to save projection:', e);
            // Re-throw so UI can show error toast
            throw e;
        }
    },

    deleteProjection: async (ticker: string, id: string): Promise<void> => {
        try {
            // 1. API Delete
            await apiDelete(ticker, id);

            // 2. Update Local Cache
            const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;
            const existing = storage.getProjections(ticker);
            const updated = existing.filter(p => p.id !== id);
            localStorage.setItem(key, JSON.stringify(updated));
        } catch (e) {
            console.error('Failed to delete projection:', e);
            throw e;
        }
    }
};
