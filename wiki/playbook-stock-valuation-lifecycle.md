# Playbook: Stock Valuation Lifecycle & Five-Surface Alignment

**Status**: CONFIRMED  
**Discovered**: 2026-08-31  
**Author**: Gemini 3.7 Flash (Self-Evolution in-situ)

---

## 1. Context & Purpose
When analyzing a stock via `update-stock-analysis`, all analytical outputs must strictly synchronize across **5 core surfaces** without hallucinating holding status or introducing ad-hoc calculations:
1. `domain_model.sqlite` (`investment`, `price_level_tier`, `projection_version`).
2. Express Backend Projection Repository (`POST /api/projections`).
3. Local disk cache (`investment_screener/backend/data/projections/{TICKER}.json`).
4. Research event timeline (`investment_screener/backend/data/research/{TICKER}.timeline.md`).
5. Frontend Valuation Modeler UI state.

---

## 2. Hard Invariants (Rules #9, #15, #21)

### Invariant A: Holdings Anchor Check Before Lifecycle Classification
* **Never guess or assume a stock is on the watchlist without checking `domain_model.sqlite`.**
* Query live holdings using the canonical script:
  ```bash
  python3 investment_screener/backend/py_services/portfolio_io.py --ticker {TICKER}
  ```
* **If `shares > 0`**:
  * `lifecycle_status`: `core` or `opportunistic`.
  * Permitted action enum: `MAINTAIN | ACCUMULATE | TRIM | EXIT` (strictly forbid `WATCHLIST`).
* **If `shares == 0`**:
  * `lifecycle_status`: `watchlist`.
  * Permitted action enum: `WATCHLIST | INITIATE`.

### Invariant B: Zero Inline Python or Ad-Hoc SQL
* Never run `python3 -c "import sqlite3; ..."` or ad-hoc SQL queries during valuation or triage.
* Use canonical CLI tools:
  * Holding check: `portfolio_io.py --ticker {TICKER}`
  * Strategy pillars: `portfolio_io.py --pillars`
  * Multi-surface write: `stock_intake_persist.py --file {payload.json}`

### Invariant C: Multi-Class Diluted Share Count
* When calculating per-share DCF values for multi-class share structures (e.g. `GOOG`/`GOOGL`), always use total diluted shares across all classes (`shares_diluted` ~12.115B) rather than a single class's count.

### Invariant D: Strategy Pillar Foreign Key Validation & Auto-Inheritance
* `domain_model.sqlite` enforces foreign key constraints on `investment.pillar_id` (`strategy_pillar`) and `investment.sub_strategy_id` (`sub_strategy`).
* When refreshing an existing holding, the persister (`stock_intake_persist.py`) will automatically validate incoming keys against `strategy_pillar` and `sub_strategy`, falling back to the existing database record if omitted or invalid.
* If manually setting a new pillar or sub-strategy, verify valid keys first via `portfolio_io.py --pillars`.

---

## 3. Standard Valuation Pipeline
```
[Step 0: Freshness Check (/api/projections/{TICKER})]
       │
       ▼
[Step 0.1: portfolio_io.py --ticker {TICKER} -> Lock IS_HELD & Permitted Actions]
       │
       ▼
[Step 1: fetch_financials.py {TICKER}]
       │
       ▼
[Step 2: standardize_metrics.py -> wacc.py -> technicals.py]
       │
       ▼
[Step 3: dcf_scenarios.py -> reverse_dcf.py]
       │
       ▼
[Step 4: stock_intake_persist.py --file {intake_payload.json}]
       │
       ▼
[Step 5: POST /api/projections with extracted projection JSON]
       │
       ▼
[Step 6: Append event to data/research/{TICKER}.timeline.md]
```
