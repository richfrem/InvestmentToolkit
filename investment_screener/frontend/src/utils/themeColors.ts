/**
 * themeColors.ts
 * =====================================
 * Purpose: the single source of category colours for pillar / sub-strategy /
 * sector groupings (Portfolio Summary donut, heatmap group headers).
 *
 * Key Functions (Index):
 *   - assignCategoryColors(kind, ids) - curated colour per id, guaranteed distinct
 *     within one chart (unknown or colliding ids get unused palette colours)
 */
export const PILLAR_COLORS: Record<string, string> = {
    compute:   '#3b82f6',
    titans:    '#8b5cf6',
    sovfin:    '#f59e0b',
    datainfra: '#06b6d4',
    power:     '#10b981',
    security:  '#ef4444',
    applied:   '#f97316',
    cash:      '#eab308',
    quantum:   '#a78bfa',
    biohealth: '#ec4899',
    quality_saas: '#6366f1',
    defense:   '#84cc16',
    photonics: '#d946ef',
    robotics:  '#14b8a6',
    other:     '#6b7280',
};

export const SECTOR_COLORS: Record<string, string> = {
    Technology:               '#3b82f6',
    'Communication Services': '#8b5cf6',
    Energy:                   '#10b981',
    Utilities:                '#34d399',
    'Financial Services':     '#f59e0b',
    Industrials:              '#fb923c',
    'Consumer Cyclical':      '#f97316',
    'Consumer Defensive':     '#a78bfa',
    Healthcare:               '#ec4899',
    'Real Estate':            '#06b6d4',
    'Basic Materials':        '#84cc16',
    CASH:                     '#eab308',
    Other:                    '#6b7280',
};

export const SUB_STRATEGY_COLORS: Record<string, string> = {
    'sa-asi-race':       '#3b82f6',
    'cybersecurity':     '#ef4444',
    'sovereign-finance': '#f59e0b',
    'quality-saas':      '#8b5cf6',
    'frontier-bets':     '#f97316',
    'quantum-compute':   '#a78bfa',
    'quantum-computing': '#a78bfa',
    'cash':              '#eab308',
    'ai-infrastructure': '#06b6d4',
    'titans-cloud':      '#6366f1',
    'power-infrastructure': '#10b981',
    'defense-ai-space':  '#84cc16',
    'memory-storage-packaging': '#0ea5e9',
    'photonics-optical': '#d946ef',
    'robotics-automation': '#14b8a6',
    'metabolic-rewriting': '#ec4899',
    'ontological-os':    '#f43f5e',
    'preipo-access':     '#b45309',
    'other':             '#6b7280',
};

// Extra distinct colours for ids without a curated entry (or whose curated colour
// is already taken in the same chart) — never one shared grey fallback.
const EXTRA_PALETTE = [
    '#f472b6', '#38bdf8', '#4ade80', '#facc15', '#c084fc', '#fb7185', '#2dd4bf', '#a3e635',
    '#fdba74', '#93c5fd', '#e879f9', '#fca5a5', '#5eead4', '#bef264', '#d8b4fe', '#fcd34d',
    '#7dd3fc', '#86efac', '#f9a8d4', '#a5b4fc',
];

export type CategoryKind = 'pillar' | 'sub-strategy' | 'sector';

const CURATED: Record<CategoryKind, Record<string, string>> = {
    'pillar': PILLAR_COLORS,
    'sub-strategy': SUB_STRATEGY_COLORS,
    'sector': SECTOR_COLORS,
};

/** Colour for each id in one chart: curated when available and unused, otherwise the
 * next unused palette colour, so no two slices/groups ever share a colour. */
export function assignCategoryColors(kind: CategoryKind, ids: string[]): Record<string, string> {
    const curated = CURATED[kind];
    const used = new Set<string>();
    const result: Record<string, string> = {};
    const extras = EXTRA_PALETTE.filter(c => !Object.values(curated).includes(c));
    let next = 0;
    for (const id of ids) {
        let color = curated[id];
        if (!color || used.has(color)) {
            while (next < extras.length && used.has(extras[next])) next++;
            color = next < extras.length ? extras[next++] : `hsl(${(ids.indexOf(id) * 137.5) % 360}, 65%, 60%)`;
        }
        used.add(color);
        result[id] = color;
    }
    return result;
}
