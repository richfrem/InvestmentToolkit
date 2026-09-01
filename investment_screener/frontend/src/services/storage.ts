
/**
 * storage.ts (TypeScript Service)
 * =====================================
 *
 * Purpose:
 *     Hybrid persistence layer that synchronizes local storage cache with the backend API.
 *     Handles schema migrations (V1 to V1.1) and ensures eventual consistency for DCF projections.
 *
 * Layer: Frontend / Services / Storage
 *
 * Usage Examples:
 *     import { storage } from './services/storage';
 *     const projections = await storage.syncProjections('AAPL');
 *
 * Key Functions:
 *     - syncProjections() - Performs a bi-directional sync between localStorage and the server, prioritizing server truth but preserving local-only USER data
 *     - saveProjection() - Validates/repairs projection objects before performing a persistent write to the API and local cache
 *     - migrateV1toV1_1() - Internal utility for upgrading legacy single-scenario projections to the modern weighted-scenario schema
 */
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
        source: 'USER',
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
        // Smart Merge: Trust Server, but preserve Local USER projections that might be missing on server (eventual consistency)
        if (serverProjections.length > 0) {
            // Find local USER projections that are NOT in server list
            const localUserOnly = localProjections.filter(lp =>
                lp.source === 'USER' &&
                !serverProjections.find(sp => sp.id === lp.id)
            );

            // Merge: Server + Missing Local
            // Note: If server has the ID, server wins.
            const merged = [...serverProjections, ...localUserOnly];

            // Update cache
            localStorage.setItem(key, JSON.stringify(merged));
            return merged;
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
            // 0. Repair Projection (Ensure validity)
            const repairProjection = (p: Projection): Projection => {
                const scenarios = p.scenarios;
                const totalWeight = (scenarios.bear.weight || 0) + (scenarios.base.weight || 0) + (scenarios.bull.weight || 0);

                if (Math.abs(totalWeight - 1.0) > 0.001 && totalWeight > 0) {
                    scenarios.bear.weight = Number((scenarios.bear.weight / totalWeight).toFixed(2));
                    scenarios.base.weight = Number((scenarios.base.weight / totalWeight).toFixed(2));
                    scenarios.bull.weight = Number((1.0 - scenarios.bear.weight - scenarios.base.weight).toFixed(2));
                }

                ['bear', 'base', 'bull'].forEach((sKey) => {
                    const s = scenarios[sKey as keyof typeof scenarios];
                    if (s.moatScore === undefined) s.moatScore = 1;
                    if (s.managementScore === undefined) s.managementScore = 1;
                });

                // Ensure Source is set (Defaults to USER if missing)
                if (!p.source) {
                    p.source = 'USER';
                }

                // Fix AI Thesis Action Enum
                if (p.aiThesis && p.aiThesis.action) {
                    const action = p.aiThesis.action.toUpperCase();
                    if (action === 'STRONG BUY') p.aiThesis.action = 'BUY';
                    else if (action === 'STRONG SELL') p.aiThesis.action = 'SELL';
                    else if (!['BUY', 'SELL', 'HOLD'].includes(action)) {
                        p.aiThesis.action = 'HOLD'; // Default fallback
                    }
                }

                // Ensure valid UUID id
                const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
                if (!p.id || !uuidRegex.test(p.id)) {
                    p.id = crypto.randomUUID();
                }

                // Ensure valid dataPreferences
                if (!p.dataPreferences) {
                    p.dataPreferences = { growthBasis: 'ttm', marginBasis: 'ttm' };
                } else {
                    if (!p.dataPreferences.growthBasis) p.dataPreferences.growthBasis = 'ttm';
                    if (!p.dataPreferences.marginBasis) p.dataPreferences.marginBasis = 'ttm';
                }

                // Ensure valid schemaVersion
                if (!p.schemaVersion || !/^1\.\d+$/.test(p.schemaVersion)) {
                    p.schemaVersion = '1.2' as any;
                }

                // Ensure valid dates
                try {
                    if (!p.updatedAt || isNaN(Date.parse(p.updatedAt))) {
                        p.updatedAt = new Date().toISOString();
                    }
                    if (!p.savedAt || isNaN(Date.parse(p.savedAt))) {
                        p.savedAt = new Date().toISOString();
                    }
                } catch (e) {
                    p.updatedAt = new Date().toISOString();
                }

                return p;
            };

            const cleanProjection = repairProjection({ ...projection });

            // 1. API Write (Strict First)
            await apiSave(cleanProjection);

            // 2. Update Local Cache on Success
            const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;
            const existing = storage.getProjections(ticker);

            // Remove old version if exists, add new to top
            const updated = [cleanProjection, ...existing.filter(p => p.id !== cleanProjection.id)];
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
    },

    toggleDefaultProjection: async (projection: { id: string, ticker: string }): Promise<void> => {
        const ticker = projection.ticker;
        const targetId = projection.id;
        const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;

        try {
            // 1. Get all current projections
            const all = storage.getProjections(ticker);

            // 2. Helper to ensure validity (weights sum to 1, etc)
            const repairProjection = (p: Projection): Projection => {
                // Ensure weights sum to 1.0
                const scenarios = p.scenarios;
                const totalWeight = (scenarios.bear.weight || 0) + (scenarios.base.weight || 0) + (scenarios.bull.weight || 0);

                if (Math.abs(totalWeight - 1.0) > 0.001 && totalWeight > 0) {
                    // Normalize
                    scenarios.bear.weight = Number((scenarios.bear.weight / totalWeight).toFixed(2));
                    scenarios.base.weight = Number((scenarios.base.weight / totalWeight).toFixed(2));
                    scenarios.bull.weight = Number((1.0 - scenarios.bear.weight - scenarios.base.weight).toFixed(2));
                }

                // Ensure required numeric fields exist (backfill defaults if missing)
                ['bear', 'base', 'bull'].forEach((sKey) => {
                    const s = scenarios[sKey as keyof typeof scenarios];
                    if (s.moatScore === undefined) s.moatScore = 1;
                    if (s.managementScore === undefined) s.managementScore = 1;
                });

                // Ensure Source is set (Defaults to USER if missing)
                if (!p.source) {
                    p.source = 'USER';
                }

                // Fix AI Thesis Action Enum
                if (p.aiThesis && p.aiThesis.action) {
                    const action = p.aiThesis.action.toUpperCase();
                    if (action === 'STRONG BUY') p.aiThesis.action = 'BUY';
                    else if (action === 'STRONG SELL') p.aiThesis.action = 'SELL';
                    else if (!['BUY', 'SELL', 'HOLD'].includes(action)) {
                        p.aiThesis.action = 'HOLD'; // Default fallback
                    }
                }

                // Ensure valid dates
                try {
                    if (!p.updatedAt || isNaN(Date.parse(p.updatedAt))) {
                        p.updatedAt = new Date().toISOString();
                    }
                    if (!p.savedAt || isNaN(Date.parse(p.savedAt))) {
                        p.savedAt = new Date().toISOString();
                    }
                } catch (e) {
                    p.updatedAt = new Date().toISOString();
                }

                return p;
            };

            // 3. Update default status & Repair
            const updates = all.map(p => {
                let updated = { ...p };

                if (targetId === 'yahoo') {
                    updated.isDefault = false;
                } else {
                    if (p.id === targetId) {
                        updated.isDefault = true;
                    } else {
                        updated.isDefault = false;
                    }
                }

                // Repair before potential save
                return repairProjection(updated);
            });

            // 4. Save modified ones to API
            for (const p of updates) {
                // Only save if changed (or if we repaired it, we might want to save? 
                // Let's safe if isDefault changed OR if we suspect repair happened. 
                // For now, simpler: save if isDefault changed. 
                // But if repair happened, we should save too? 
                // The issue is repair might change fields that make it 'changed'.
                // Let's save if isDefault changed. The repair is just to make the SAVE succeed.

                const original = all.find(old => old.id === p.id);
                if (original && p.isDefault !== original.isDefault) {
                    await apiSave(p);
                }
            }

            // 5. Update Local Cache
            localStorage.setItem(key, JSON.stringify(updates));

        } catch (e) {
            console.error("Failed to toggle default:", e);
            throw e;
        }
    }
};
