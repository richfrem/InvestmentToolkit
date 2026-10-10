/**
 * pillars.ts - Group position rows by strategy pillar for the master thesis.
 *
 * Purpose:
 *     The master thesis lists the portfolio by pillar (Compute, Security, Power ...), each with
 *     its stocks and how their combined weight compares with the pillar's target. This groups the
 *     shared position rows that way, using the pillar names and target weights from the
 *     database (GET /api/theses/pillars). Pure, so the grouping and ordering are unit tested.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const groups = groupByPillar(rows, pillars);
 *
 * Key Functions (Index):
 *     - Pillar: a strategy pillar as the API returns it
 *     - groupByPillar(): rows grouped under their pillar, largest target first, unknown pillars under Other
 *
 * Key Input Dependencies:
 *     - positionMath (PositionRow), GET /api/theses/pillars
 *
 * Key Output Dependencies:
 *     - MasterPositions
 */
import type { PositionRow } from './positionMath';

export interface Pillar {
    id: string;
    name: string;
    targetWeight: number | null;
}

export interface PillarGroup {
    pillarId: string;
    name: string;
    /** The pillar's own target weight from the pillars list (null for Other). */
    pillarTarget: number | null;
    rows: PositionRow[];
    /** Summed actual and target weight of the stocks in this group. */
    actualPct: number;
    targetPct: number;
}

const OTHER = 'other';

/** Rows grouped by pillar, ordered by the pillar's target weight (largest first); unknown pillars go last as Other. */
export function groupByPillar(rows: PositionRow[], pillars: Pillar[]): PillarGroup[] {
    const known = new Map(pillars.map(p => [p.id, p]));
    const buckets = new Map<string, PositionRow[]>();
    for (const row of rows) {
        const key = known.has(row.pillarId) ? row.pillarId : OTHER;
        (buckets.get(key) ?? buckets.set(key, []).get(key)!).push(row);
    }
    const groups: PillarGroup[] = [];
    for (const [key, members] of buckets) {
        const pillar = known.get(key);
        groups.push({
            pillarId: key,
            name: pillar?.name ?? 'Other',
            pillarTarget: pillar?.targetWeight ?? null,
            rows: members,
            actualPct: members.reduce((s, r) => s + (r.actualPct ?? 0), 0),
            targetPct: members.reduce((s, r) => s + (r.targetPct ?? 0), 0),
        });
    }
    return groups.sort((a, b) => {
        if (a.pillarId === OTHER) return 1;
        if (b.pillarId === OTHER) return -1;
        return (b.pillarTarget ?? 0) - (a.pillarTarget ?? 0) || a.name.localeCompare(b.name);
    });
}
