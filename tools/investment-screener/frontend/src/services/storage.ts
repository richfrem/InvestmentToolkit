
// LocalStorage service for Saved Projections

export interface SavedProjection {
    id: string;
    ticker: string;
    savedAt: string; // ISO string
    name?: string;   // User note (optional)
    scenarios: {
        growthRate: number;
        netMargin: number;
        exitPE: number;
        shareChange: number;
        discountRate: number;
        timeHorizon: number;
        terminalGrowth: number;
    };
}

const STORAGE_PREFIX = 'projections_';

export const storage = {
    // Get all projections for a ticker
    getProjections: (ticker: string): SavedProjection[] => {
        try {
            const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;
            const data = localStorage.getItem(key);
            if (!data) return [];
            return JSON.parse(data);
        } catch (e) {
            console.error('Failed to load projections:', e);
            return [];
        }
    },

    // Save a new projection
    saveProjection: (projection: SavedProjection): void => {
        try {
            const key = `${STORAGE_PREFIX}${projection.ticker.toUpperCase()}`;
            const existing = storage.getProjections(projection.ticker);

            // Add to start of array (newest first)
            const updated = [projection, ...existing];
            localStorage.setItem(key, JSON.stringify(updated));
        } catch (e) {
            console.error('Failed to save projection:', e);
        }
    },

    // Delete a projection by ID
    deleteProjection: (ticker: string, id: string): void => {
        try {
            const key = `${STORAGE_PREFIX}${ticker.toUpperCase()}`;
            const existing = storage.getProjections(ticker);
            const updated = existing.filter(p => p.id !== id);
            localStorage.setItem(key, JSON.stringify(updated));
        } catch (e) {
            console.error('Failed to delete projection:', e);
        }
    },

    // Clear all saved data for a ticker
    clearProjections: (ticker: string): void => {
        localStorage.removeItem(`${STORAGE_PREFIX}${ticker.toUpperCase()}`);
    }
};
