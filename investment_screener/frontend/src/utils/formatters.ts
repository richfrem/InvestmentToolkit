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

// Heatmap background for daily/period % change (tight thresholds ±8%)
export function changeBgDaily(v: number | null): string {
    if (v == null) return 'transparent';
    if (v >=  8) return 'rgba(0,77,0,0.85)';
    if (v >=  5) return 'rgba(0,102,0,0.80)';
    if (v >=  3) return 'rgba(0,128,0,0.75)';
    if (v >=  2) return 'rgba(0,160,0,0.70)';
    if (v >=  1) return 'rgba(0,192,0,0.65)';
    if (v >=  0.5) return 'rgba(0,220,0,0.55)';
    if (v >=  0) return 'rgba(30,180,30,0.30)';
    if (v >= -0.5) return 'rgba(200,30,30,0.30)';
    if (v >= -1) return 'rgba(210,0,0,0.55)';
    if (v >= -2) return 'rgba(185,0,0,0.65)';
    if (v >= -3) return 'rgba(160,0,0,0.70)';
    if (v >= -5) return 'rgba(130,0,0,0.75)';
    if (v >= -8) return 'rgba(100,0,0,0.80)';
    return 'rgba(70,0,0,0.85)';
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
