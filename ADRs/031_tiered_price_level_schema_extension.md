# ADR-031: Tiered Price Level Schema Extension

**Status**: ACCEPTED
**Date**: 2026-06-21
**Author**: Antigravity (Gemini 2.5 Pro)
**Implements**: Phase 1–5 of the Price Levels Plan
**Related files**:
- `plugins/portfolio-advisor/scripts/update_price_levels.py` (new)
- `investment_screener/backend/src/utils/zod-schemas.ts` (modified)
- `investment_screener/backend/data/theses/target-portfolio.json` (extended)
- `investment_screener/backend/data/portfolio.json` (extended)

**Renumbered 2026-07-22** from `docs/architecture/ADR-price-levels-schema.md` into the canonical
`ADRs/` sequence (was previously outside the numbered ADR history). No content change beyond this
header and the superseded-schema note directly below.

**Superseded schema note (Domain Data Model v3.2 migration):** the `target-portfolio.json`
`priceLevels` block this ADR describes was migrated into SQLite's `price_level_set`/
`price_level_tier` tables in Wave 2 (see `docs/superpowers/status/wave2-target-portfolio-report.md`).
The `portfolio.json` `priceLevelSnapshot` block this ADR describes was found in Wave 3 to be **dead
code in production** — the pre-migration read path checked a JSON shape (`accounts[]`) that real
`portfolio.json` never had, so `snapshot_written` was always `False` and nothing was ever actually
written there. Wave 3 replaced it with `compute_price_level_snapshot_from_db()`, deriving the same
`{nextBuyTier, nextSellTier, stopLoss, proximityFlags}` shape live from `price_level_tier` +
`investment_price` — no JSON snapshot is written or read for this purpose anymore. The formulas,
source hierarchy, and skill-integration table below remain accurate as the *business logic* this
ADR established; only the storage location changed.

---

## Context

The toolkit had no machine-readable buy or sell price levels. Entry and exit prices
from DCF analysis were buried in free-text `agentRationale` strings. This meant:

- `/tv-alert-sync` could only set coarse bear/base/bull scenario alerts
- `/rebalance` could not distinguish "intentional limit order near tier" from "drift correction"
- `/ta-daily-sweep` flagged `NEAR_FV` but could not say *which tier* was approaching
- Catalysts from `/x-news-sweep` shifted scenario weights but did not propagate to
  actionable price levels the user could act on immediately

---

## Decision

Extend both canonical data files with structured price level blocks:

### `target-portfolio.json` — `priceLevels` per holding

```jsonc
"priceLevels": {
  "schemaVersion": "1.0",
  "lastUpdated": "YYYY-MM-DD",
  "lastUpdatedBy": "dcf",          // which skill last wrote this
  "buyTiers":  [ ...PriceTier[] ], // up to 5 entries, ordered by tier number
  "sellTiers": [ ...PriceTier[] ], // trim 30% / 50% / exit 100%
  "stopLoss":  StopLoss            // thesis breaker price
}
```

### `portfolio.json` — `priceLevelSnapshot` per holding (read-only, denormalized)

```jsonc
"priceLevelSnapshot": {
  "nextBuyTier":  PriceTier | null,
  "nextSellTier": PriceTier | null,
  "stopLoss":     StopLoss  | null,
  "proximityFlags": string[]        // computed on sync, e.g. "AT_SELL_TIER_1"
}
```

### Canonical derivation formulas (source = "dcf")

| Tier | Formula | Rationale |
|------|---------|-----------|
| buyTier[1].price | `base_fv × 0.75` | 25% margin of safety |
| buyTier[2].price | `bear_fv × 1.05` | Just above bear scenario |
| sellTier[1].price | `base_fv` | Trim 30% — DCF says fully valued |
| sellTier[2].price | `bull_fv` | Trim 50% — DCF says richly valued |
| sellTier[3].price | `bull_fv × 1.20` | Exit 100% — thesis fully priced in |
| stopLoss.price | `bear_fv × 0.95` | Thesis breaker |

### Source hierarchy (additive, not replacing)

1. `dcf` — derived from `projections/{TICKER}.json` scenarioPrice values
2. `ta` — from `/tv-ta-deep` Phase 5 synthesis (EMA zones, support/resistance)
3. `news` / `earnings` — re-derived after `apply_catalyst.py` updates scenarios
4. `13f` — smart money confirmation signals
5. `manual` — user override

When multiple sources exist for the same tier, all are stored. Skills show both for
context; user decides which to act on.

---

## Consequences

### Positive

- `/tv-alert-sync` now creates tiered alerts: "Trim 30% at $518", "Exit at $720", "⚠️ Stop $310"
- `/ta-daily-sweep` emits `AT_SELL_TIER_1` flags when price approaches a tier
- `/rebalance` distinguishes tier-approach limit orders from drift correction market orders
- `/daily` triage cards show "Price Level Alert" cards when within 2% of any tier
- Triggered tiers are never deleted — `status: "triggered"` preserves history
- Schema is fully backward-compatible — all fields optional, `.passthrough()` on ThesisHoldingSchema

### Constraints

- `portfolio.json` `priceLevelSnapshot` is always **derived** — never hand-edited
- DCF tiers are always computed by formula — never hand-keyed for `source: "dcf"` entries
- TA tiers never replace DCF tiers (additive)
- `update_price_levels.py` requires `--write` explicitly (dry-run is the default)
- Triggered tiers get `status: "triggered"` + `triggeredAt` timestamp — never deleted

---

## Alternatives Considered

1. **Store levels only in `projections/{TICKER}.json`** — rejected because projections
   are valuation-focused (bear/base/bull scenarios) and skills already have to join two
   files. A third location adds more join complexity.

2. **Embed levels in `agentRationale` free text** — rejected because machine-readable
   skills cannot reliably parse natural language for exact prices.

3. **Separate `price-levels.json` per ticker** — rejected because it fragments the
   canonical source of truth. `target-portfolio.json` is already the single authority
   for thesis metadata; `priceLevels` belongs alongside the holding it describes.

---

## Implementation Notes

- `update_price_levels.py` uses the same `locked_write_json` atomic write pattern as
  `update_targets.py` — safe for concurrent Python + Node access
- Zod schemas use `.passthrough()` on `ThesisHoldingSchema` to allow `agentRationale`,
  `shares`, `subStrategyId` and any other free fields without validation errors
- The `tickerRegex` constant was moved to module scope (before the price level schemas)
  so it can be referenced by both `ThesisHoldingSchema` and `PortfolioHoldingSchema`
- Tests live at `investment_screener/backend/tests/py_services/test_update_price_levels.py`

---

## Skill Integration Summary

| Skill | Change |
|-------|--------|
| `stock_valuation` | Calls `update_price_levels.py --source dcf` after saving projection |
| `x-news-sweep` | Step 6b: re-derives tiers after `apply_catalyst.py` |
| `ta-daily-sweep` | Reads `priceLevelSnapshot.proximityFlags` for tier-approach alerts |
| `technical_analysis_expert` | Offers to write TA tiers after Phase 5 synthesis |
| `tv-alert-sync` | Reads `priceLevels` tiers first (richer labels), falls back to scenario prices |
| `rebalance-portfolio` | Surfaces tier-approach limit orders before drift correction trades |
| `daily-loop-agent` | Adds Price Level Alert Cards in triage when within 2% of any tier |
| `tv-portfolio-sync` | Computes `priceLevelSnapshot` during sync denormalization |
