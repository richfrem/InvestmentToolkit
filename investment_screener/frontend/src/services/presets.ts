/**
 * presets.ts (TypeScript Service)
 * =====================================
 *
 * Purpose:
 *     Client-side persistence layer for managing user-defined valuation presets in localStorage.
 *
 * Layer: Frontend / Services / Storage
 *
 * Usage Examples:
 *     import { loadUserPresets } from './services/presets';
 *     const presets = loadUserPresets('AAPL');
 *
 * Key Functions:
 *     - saveUserPreset() - Creates and persists a new valuation configuration for a specific symbol
 *     - loadUserPresets() - Filters and retrieves all user-saved presets for a given ticker
 *     - deleteUserPreset() - Removes a specific preset from localStorage by its unique ID
 */

export interface UserPreset {
    id: string;
    name: string;
    symbol: string;
    scenarios: {
        bear: {
            growthRate: number;
            netMargin: number;
            exitPE: number;
            qualityMultiplier: number;
            shareChange: number;
            weight: number;
        };
        base: {
            growthRate: number;
            netMargin: number;
            exitPE: number;
            qualityMultiplier: number;
            shareChange: number;
            weight: number;
        };
        bull: {
            growthRate: number;
            netMargin: number;
            exitPE: number;
            qualityMultiplier: number;
            shareChange: number;
            weight: number;
        };
    };
    globalSettings: {
        timeHorizon: number;
        discountRate: number;
    };
    savedAt: string; // ISO date
    description?: string;
}

const STORAGE_KEY = 'userPresets';

/**
 * Save a new user preset to localStorage
 */
export function saveUserPreset(
    symbol: string,
    name: string,
    scenarios: UserPreset['scenarios'],
    globalSettings: UserPreset['globalSettings'],
    description?: string
): UserPreset {
    const preset: UserPreset = {
        id: `preset_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        name,
        symbol,
        scenarios,
        globalSettings,
        savedAt: new Date().toISOString(),
        description
    };

    const existing = loadAllUserPresets();
    existing.push(preset);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));

    return preset;
}

/**
 * Load all user presets for a specific symbol
 */
export function loadUserPresets(symbol: string): UserPreset[] {
    const all = loadAllUserPresets();
    return all.filter(p => p.symbol === symbol);
}

/**
 * Load all user presets (across all symbols)
 */
function loadAllUserPresets(): UserPreset[] {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch (error) {
        console.error('Failed to load user presets:', error);
        return [];
    }
}

/**
 * Delete a user preset by ID
 */
export function deleteUserPreset(id: string): void {
    const existing = loadAllUserPresets();
    const filtered = existing.filter(p => p.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
}

/**
 * Update an existing preset
 */
export function updateUserPreset(id: string, updates: Partial<Omit<UserPreset, 'id' | 'symbol' | 'savedAt'>>): void {
    const existing = loadAllUserPresets();
    const index = existing.findIndex(p => p.id === id);

    if (index !== -1) {
        existing[index] = {
            ...existing[index],
            ...updates,
            savedAt: new Date().toISOString() // Update timestamp
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
    }
}
