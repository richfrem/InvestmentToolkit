/**
 * PriceLevelRepository.ts - SQLite persistence for `price_level_set`/`price_level_tier`.
 *
 * Purpose:
 *   TS-side counterpart to `py_services/domain_model/price_level_repository.py`
 *   (Wave 8), reading/writing the same physical `data/domain_model.sqlite` file
 *   via `better-sqlite3`. Mirrors that module's exact contract: full-replace
 *   semantics per investment (delete-then-reinsert the whole price-level set,
 *   matching update_price_levels.py's own always-rewrite-the-whole-object
 *   pattern), and the same BUY_TIER/SELL_TIER/STOP_LOSS/TARGET_ENTRY tier_kind
 *   convention.
 *
 * Layer:
 *   Backend / Services / Data Persistence (SQLite-backed repository)
 *
 * Key Functions (Index):
 *   - replacePriceLevels(investmentId, ...) - Delete-then-reinsert the whole
 *     price_level_set/price_level_tier rows for one investment
 *   - getPriceLevels(investmentId) - Read helper mirroring
 *     price_level_repository.py::get_price_levels's return shape
 */
import Database from 'better-sqlite3';

export interface PriceTierRow {
    tier: number;
    price: number | null;
    action?: string | null;
    trimPct?: number | null;
    orderType?: string | null;
    basis?: string | null;
    source?: string | null;
    sourceDate?: string | null;
    condition?: string | null;
    status?: string | null;
}

export interface StopLossRow {
    price: number | null;
    basis?: string | null;
    source?: string | null;
    sourceDate?: string | null;
    type?: string | null;
    status?: string | null;
}

export interface PriceLevelSetResult {
    priceLevelSetId: string;
    schemaVersion: string | null;
    lastUpdated: string | null;
    lastUpdatedBy: string | null;
    note: string | null;
    buyTiers: PriceTierRow[];
    sellTiers: PriceTierRow[];
    stopLoss: StopLossRow | null;
    targetEntryPrice: number | null;
}

export class PriceLevelRepository {
    private db: Database.Database;

    constructor(dbPath: string) {
        this.db = new Database(dbPath);
        this.ensureSchema();
    }

    close(): void {
        this.db.close();
    }

    private ensureSchema(): void {
        this.db.pragma('journal_mode = WAL');
        this.db.exec(`
            CREATE TABLE IF NOT EXISTS price_level_set (
                price_level_set_id  TEXT PRIMARY KEY,
                investment_id       TEXT NOT NULL,
                schema_version      TEXT,
                last_updated        TEXT,
                last_updated_by     TEXT,
                note                TEXT
            );
            CREATE TABLE IF NOT EXISTS price_level_tier (
                tier_id              TEXT PRIMARY KEY,
                price_level_set_id   TEXT NOT NULL,
                tier_kind            TEXT NOT NULL DEFAULT 'BUY_TIER',
                tier_number          INTEGER NOT NULL,
                price                REAL,
                action               TEXT,
                trim_pct             REAL,
                order_type           TEXT,
                basis                TEXT,
                source               TEXT,
                source_date          TEXT,
                condition            TEXT,
                status               TEXT
            );
        `);
    }

    replacePriceLevels(
        investmentId: string,
        schemaVersion: string | null,
        lastUpdated: string | null,
        lastUpdatedBy: string | null,
        note: string | null,
        buyTiers: PriceTierRow[],
        sellTiers: PriceTierRow[],
        stopLoss: StopLossRow | null,
        targetEntryPrice: number | null
    ): string {
        const existing = this.db
            .prepare('SELECT price_level_set_id FROM price_level_set WHERE investment_id = ?')
            .get(investmentId) as { price_level_set_id: string } | undefined;
        if (existing) {
            this.db.prepare('DELETE FROM price_level_tier WHERE price_level_set_id = ?').run(existing.price_level_set_id);
            this.db.prepare('DELETE FROM price_level_set WHERE price_level_set_id = ?').run(existing.price_level_set_id);
        }

        const priceLevelSetId = `${investmentId}-pls-${Math.random().toString(16).slice(2, 10)}`;
        this.db
            .prepare(
                `INSERT INTO price_level_set
                 (price_level_set_id, investment_id, schema_version, last_updated, last_updated_by, note)
                 VALUES (?, ?, ?, ?, ?, ?)`
            )
            .run(priceLevelSetId, investmentId, schemaVersion, lastUpdated, lastUpdatedBy, note);

        const insertTier = (tierKind: string, tier: PriceTierRow) => {
            const tierId = `${priceLevelSetId}-${tierKind}-${tier.tier ?? Math.random().toString(16).slice(2, 8)}`;
            this.db
                .prepare(
                    `INSERT INTO price_level_tier
                     (tier_id, price_level_set_id, tier_kind, tier_number, price, action,
                      trim_pct, order_type, basis, source, source_date, condition, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
                )
                .run(
                    tierId, priceLevelSetId, tierKind, tier.tier ?? 0, tier.price ?? null,
                    tier.action ?? null, tier.trimPct ?? null, tier.orderType ?? null,
                    tier.basis ?? null, tier.source ?? null, tier.sourceDate ?? null,
                    tier.condition ?? null, tier.status ?? null
                );
        };

        for (const tier of buyTiers) insertTier('BUY_TIER', tier);
        for (const tier of sellTiers) insertTier('SELL_TIER', tier);

        if (stopLoss) {
            const tierId = `${priceLevelSetId}-STOP_LOSS`;
            this.db
                .prepare(
                    `INSERT INTO price_level_tier
                     (tier_id, price_level_set_id, tier_kind, tier_number, price, basis,
                      source, source_date, condition, status)
                     VALUES (?, ?, 'STOP_LOSS', 0, ?, ?, ?, ?, ?, ?)`
                )
                .run(
                    tierId, priceLevelSetId, stopLoss.price ?? null, stopLoss.basis ?? null,
                    stopLoss.source ?? null, stopLoss.sourceDate ?? null, stopLoss.type ?? null,
                    stopLoss.status ?? null
                );
        }

        if (targetEntryPrice !== null && targetEntryPrice !== undefined) {
            const tierId = `${priceLevelSetId}-TARGET_ENTRY`;
            this.db
                .prepare(
                    `INSERT INTO price_level_tier
                     (tier_id, price_level_set_id, tier_kind, tier_number, price)
                     VALUES (?, ?, 'TARGET_ENTRY', 0, ?)`
                )
                .run(tierId, priceLevelSetId, targetEntryPrice);
        }

        return priceLevelSetId;
    }

    getPriceLevels(investmentId: string): PriceLevelSetResult | null {
        const setRow = this.db
            .prepare('SELECT * FROM price_level_set WHERE investment_id = ?')
            .get(investmentId) as
            | { price_level_set_id: string; schema_version: string | null; last_updated: string | null; last_updated_by: string | null; note: string | null }
            | undefined;
        if (!setRow) return null;

        const tiers = this.db
            .prepare('SELECT * FROM price_level_tier WHERE price_level_set_id = ? ORDER BY tier_number')
            .all(setRow.price_level_set_id) as Array<{
                tier_kind: string; tier_number: number; price: number | null; action: string | null;
                trim_pct: number | null; order_type: string | null; basis: string | null;
                source: string | null; source_date: string | null; condition: string | null; status: string | null;
            }>;

        const toTierRow = (t: (typeof tiers)[number]): PriceTierRow => ({
            tier: t.tier_number, price: t.price, action: t.action, trimPct: t.trim_pct,
            orderType: t.order_type, basis: t.basis, source: t.source, sourceDate: t.source_date,
            condition: t.condition, status: t.status,
        });

        const stopLossTier = tiers.find(t => t.tier_kind === 'STOP_LOSS');
        const targetEntryTier = tiers.find(t => t.tier_kind === 'TARGET_ENTRY');

        return {
            priceLevelSetId: setRow.price_level_set_id,
            schemaVersion: setRow.schema_version,
            lastUpdated: setRow.last_updated,
            lastUpdatedBy: setRow.last_updated_by,
            note: setRow.note,
            buyTiers: tiers.filter(t => t.tier_kind === 'BUY_TIER').map(toTierRow),
            sellTiers: tiers.filter(t => t.tier_kind === 'SELL_TIER').map(toTierRow),
            stopLoss: stopLossTier
                ? { price: stopLossTier.price, basis: stopLossTier.basis, source: stopLossTier.source, sourceDate: stopLossTier.source_date, type: stopLossTier.condition, status: stopLossTier.status }
                : null,
            targetEntryPrice: targetEntryTier ? targetEntryTier.price : null,
        };
    }
}
