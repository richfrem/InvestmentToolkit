export function safeNum(v: any): number | null {
    if (v == null || v === '' || typeof v === 'boolean') return null;
    const n = Number(v);
    return isNaN(n) ? null : n;
}

export function fmtPct(v: any): string {
    const n = safeNum(v);
    if (n == null) return '—';
    return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

export function fmtDollar(v: any): string {
    const n = safeNum(v);
    if (n == null) return '—';
    if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
    if (n >= 1_000)     return `$${(n / 1_000).toFixed(1)}K`;
    return `$${n.toFixed(0)}`;
}

export function fmtPrice(v: any): string {
    const n = safeNum(v);
    return n != null ? `$${n.toFixed(2)}` : '—';
}

// ─── % change colour ladder (single source: AGENTS.md rule 22) ─────────────────
// One set of 1-day thresholds, two palettes: `changeBgDaily` for table cells and
// `changeTileColor` for heatmap tiles. `scale` widens the thresholds for longer
// periods (see priceChangePeriods.periodScale), so 1Y moves don't all saturate.
const CHANGE_THRESHOLDS = [8, 5, 3, 2, 1, 0.5, 0, -0.5, -1, -2, -3, -5, -8];
const CELL_PALETTE = [
    'rgba(0,77,0,0.85)', 'rgba(0,102,0,0.80)', 'rgba(0,128,0,0.75)', 'rgba(0,160,0,0.70)',
    'rgba(0,192,0,0.65)', 'rgba(0,220,0,0.55)', 'rgba(30,180,30,0.30)', 'rgba(200,30,30,0.30)',
    'rgba(210,0,0,0.55)', 'rgba(185,0,0,0.65)', 'rgba(160,0,0,0.70)', 'rgba(130,0,0,0.75)',
    'rgba(100,0,0,0.80)', 'rgba(70,0,0,0.85)',
];
const TILE_PALETTE = [
    '#004d00', '#006600', '#008000', '#00a000', '#00c000', '#00e000', '#40ff40',
    '#ff6060', '#e00000', '#c00000', '#a00000', '#800000', '#600000', '#400000',
];
export const NO_DATA_TILE_COLOR = '#3f3f46';

/** Index into the palettes: first threshold (scaled) the value reaches; last = below all. */
function changeLevel(v: number, scale: number): number {
    const i = CHANGE_THRESHOLDS.findIndex(t => v >= t * scale);
    return i === -1 ? CHANGE_THRESHOLDS.length : i;
}

// Table cell background for daily/period % change
export function changeBgDaily(v: number | null, scale = 1): string {
    if (v == null || !Number.isFinite(v)) return 'transparent';
    return CELL_PALETTE[changeLevel(v, scale)];
}

// Heatmap tile colour for daily/period % change
export function changeTileColor(v: number | null, scale = 1): string {
    if (v == null || !Number.isFinite(v)) return NO_DATA_TILE_COLOR;
    return TILE_PALETTE[changeLevel(v, scale)];
}

// Heatmap background for DCF upside % (wide thresholds ±50%)
export function changeBgUpside(v: number | null): string {
    if (v == null) return 'transparent';
    if (v >=  50) return 'rgba(0,102,0,0.85)';
    if (v >=  25) return 'rgba(0,160,0,0.70)';
    if (v >=  10) return 'rgba(0,220,0,0.40)';
    if (v >=   0) return 'rgba(30,180,30,0.20)';
    if (v >= -10) return 'rgba(200,30,30,0.20)';
    if (v >= -25) return 'rgba(210,0,0,0.50)';
    return 'rgba(120,0,0,0.80)';
}

export function deltaColor(value: number): string {
    if (value > 0) return 'text-emerald-400';
    if (value < 0) return 'text-red-400';
    return 'text-slate-400';
}

export function sortByColumn<T>(rows: T[], col: keyof T, dir: 'asc' | 'desc'): T[] {
    return [...rows].sort((a, b) => {
        const av = a[col], bv = b[col];
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        const cmp = av < bv ? -1 : av > bv ? 1 : 0;
        return dir === 'asc' ? cmp : -cmp;
    });
}
