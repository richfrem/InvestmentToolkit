# Architecture: Valuation Persistence (v1.1)

This document outlines the design for persisting user-defined valuations and AI suggestions to a permanent backend store, moving beyond the current `LocalStorage` implementation.

## 1. Problem Statement
The current `LocalStorage` persistence is browser-bound and lost if the browser cache is cleared. For a professional toolkit, valuations (and the AI reasoning behind them) must be:
1. **Persistent**: Stored as version-controlled project data on disk.
2. **Atomic**: Resist corruption even during hard crashes/power loss.
3. **Traceable**: Capture exact financial snapshots so projections can be reconstructed years later.

## 2. Updated Architecture

### 2.1 Storage Model: Per-Ticker Sharding
Instead of a single monolithic JSON file, we will use individual files to ensure isolation and performance.
- **Root**: `backend/data/projections/`
- **File**: `{TICKER}.json` (e.g., `NVDA.json`)
- **Writing**: Every write must be **atomic**. Write to `.tmp` file first, then `fs.renameSync()` to the target.

### 2.2 API Layer & Security
New endpoints in `backend/src/index.ts` with **Zod Schema Validation**:
- `GET /api/projections/:ticker`: Fetch all saved projections for a stock.
- `POST /api/projections`: 
  - **Validation**: Strict schema check on growth, margins, and probability weights (Sum = 1.0).
  - **Constraint**: Payload limit set to 50KB to prevent bloat/DoS.
  - **Concurrency**: Basic file-locking using `proper-lockfile` to prevent read-modify-write races.
- `DELETE /api/projections/:ticker/:id`: Remove a specific projection.

### 2.3 Synchronization: API-First
The `storage.ts` service will transition to a **Strict API-First** model:
1. **Save Flow**: POST to API → On Success → Update LocalStorage cache.
2. **Conflict Detection**: Every projection includes a `version` (int) and `updatedAt` (ISO). Backend rejects saves with stale versions (409 Conflict).
3. **Migration**: Client-side logic will detect V1.0 (flat) `LocalStorage` data, run a migration transformation, and push to the backend on first load.

## 3. Data Schema
The JSON structure will preserve the full mult-scenario context and historical snapshots.

```json
{
  "ticker": "NVDA",
  "id": "171...",
  "schemaVersion": "1.1",
  "version": 12,
  "savedAt": "2026-02-14T17:18:35Z",
  "updatedAt": "2026-02-14T17:18:35Z",
  "name": "Q1 2026 Deep Dive",
  "rationale": "Overall investment thesis: Dominance in AI silicon and networking.",
  "snapshot": {
    "price": 136.21,
    "shares": 24500000000,
    "revenue": 96000000000,
    "fiscalPeriod": "TTM ending Q4 2025",
    "analystGrowthEstimate": 66.7,
    "analystMarginEstimate": 53.0,
    "currency": "USD"
  },
  "dataPreferences": {
    "growthBasis": "next",
    "marginBasis": "ttm"
  },
  "scenarios": {
    "bear": {
      "weight": 0.20,
      "growthRate": 30.0,
      "netMargin": 35.0,
      "exitPE": 15,
      "qualityMultiplier": 1.0,
      "shareChange": 2.0,
      "rationale": "Risk of CSPs insourcing chips and competition from AMD."
    },
    "base": {
      "weight": 0.60,
      "growthRate": 65.5,
      "netMargin": 48.0,
      "exitPE": 25,
      "qualityMultiplier": 1.5,
      "shareChange": -2.0,
      "rationale": "Continued AI infra spend..."
    },
    "bull": {
      "weight": 0.20,
      "growthRate": 85.0,
      "netMargin": 52.0,
      "exitPE": 35,
      "qualityMultiplier": 1.8,
      "shareChange": -5.0,
      "rationale": "Total market dominance."
    }
  },
  "aiThesis": {
    "model": "gemini-3-flash-preview",
    "rationale": "NVDA's 62.5% growth and 128.51 Rule of 40 score...",
    "fairValue": 439.69,
    "action": "BUY",
    "analyzedAt": "2026-02-14..."
  },
  "globalSettings": {
    "discountRate": 10.0,
    "timeHorizon": 5
  }
}
```

## 4. Migration Registry
We will maintain an internal migration chain in the frontend `storage.ts`:
- **V1.0 (Current)**: Flat settings object.
- **V1.1 (Target)**: Mult-scenario with snapshots and weighted fair value.
- **Logic**: `migrateV1toV1_1` maps old `growthRate` to `base.growthRate` with `weight: 1.0`.

## 5. Security & Verification
- **Input Validation**: Tickers sanitized via `isValidTicker()`.
- **Atomic Renames**: Protect against mid-write crashes.
- **Weight Check**: Sum of bear/base/bull weights MUST be 1.00 ± 0.01.
