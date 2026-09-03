# ADR-031: Unified 5-Surface Synchronization Engine & Atomic Persistence

- **Status**: Accepted
- **Date**: 2026-08-25
- **Author**: Antigravity Reasoning Agent & Peer Review Council

---

## Context
When conducting stock intake (`/stock-intake`) or deep valuation refresh (`/update-stock-analysis`), the InvestmentToolkit renders analytical conclusions across 5 distinct UI surfaces:
1. **Overview Tab & Strategy** (`domain_model.sqlite` `investment` table)
2. **Technicals Tab** (`intelligence.sqlite` `TECHNICAL_SWEEP` & `domain_model.sqlite` `price_level_tier`)
3. **Valuation Modeler Tab** (`domain_model.sqlite` `projection_version` & `/api/projections`)
4. **Research Deep-Dive Modal** (`data/research/{TICKER}_{DATE}.md` view from `intelligence_event`)
5. **TradingView Desktop Overlay** (Pine Script indicator on TradingView CDP port 9222)

Previously, agents performed disparate, uncoordinated writes across these systems. Furthermore, persistence lacked transactional guarantees: partial commits left database rows in an inconsistent state when downstream operations failed, violating the core integrity principle of the platform.

---

## Decision

### 1. Unified 5-Surface Architecture & Implementation Status
All stock analysis and valuation refreshes must synchronize the 5 visual surfaces using canonical tooling:

| # | UI Surface | Data Store | Canonical Script / Handler | Implementation Status |
|---|---|---|---|---|
| 1 | **Overview Tab** | `domain_model.sqlite` (`investment`) | `py_services/stock_intake_persist.py` | **Shipped & Tested** |
| 2 | **Technicals Tab** | `intelligence.sqlite` & `price_level_tier` | `plugins/tradingview/scripts/ta_sweep_single.py` | **Shipped & Tested** |
| 3 | **Valuation Modeler** | `domain_model.sqlite` (`projection_version`) & JSON | `py_services/stock_intake_persist.py` | **Shipped & Tested** |
| 4 | **Research Deep-Dive** | `intelligence.sqlite` (`intelligence_event`) | `intelligence/view_generator.py` | **Shipped & Tested** |
| 5 | **TradingView Overlay** | Live TV Desktop DOM / Pine Editor | `plugins/tradingview/scripts/tv_thesis_overlay.py` | **Shipped & Tested** |

### 2. Transactional Atomicity Guarantee (`stock_intake_persist.py`)
To prevent partial-state corruption:
- Multi-table database modifications (`investment`, `price_level_tier`, `projection_version`) must execute within an explicit `BEGIN IMMEDIATE ... COMMIT` block.
- Any error during metadata update or price level replacement triggers an immediate `ROLLBACK`.
- Disk JSON projection updates (`data/projections/{TICKER}.json`) execute **only after** the DB transaction successfully commits, using atomic write-to-temp-then-rename (`tempfile.NamedTemporaryFile` + `os.replace`).

### 3. Non-Holding Safety Guard (`validate_stock_metrics.py`)
Non-holdings (broker shares held $\le 0$) cannot have action recommendations of `TRIM`, `EXIT`, `MAINTAIN`, or `ACCUMULATE`. Only `INITIATE`, `WATCHLIST`, or `AVOID` are permitted.

---

## Consequences
- Eliminates cross-surface staleness and desynchronization.
- Prevents database corruption from partial persistence failures.
- Enforces strict compliance with Self-Evolution Rule 12 (Modular validation functions with zero ad-hoc scripting).
