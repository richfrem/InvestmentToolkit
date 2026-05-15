# Task 0001: TradingView Data Abstraction Layer

## Goal
Replace hard Questrade API dependencies with a broker-agnostic data layer that can read accounts, holdings, balances, and positions from **TradingView's CDP DOM** as the primary source — making the toolkit useful to any TradingView user regardless of broker. Questrade direct API integration remains available as an optional, opt-in path.

## Motivation
- Questrade personal app registrations are read-only (no order placement via REST)
- TradingView already holds live account data (positions, P&L, buying power) for any connected broker
- The `/place-order` skill already demonstrates that CDP automation can interact with TradingView's broker panel
- Removing the Questrade-as-required dependency broadens the toolkit's audience to all TradingView Premium users

## Architecture: Abstraction Layer

### New module: `plugins/tradingview/node/core/broker_data.js`
CDP DOM scraper that reads TradingView's broker panel and returns structured data:

```js
getBrokerAccounts()   → [{ accountId, accountType, currency, buyingPower }]
getBrokerPositions()  → [{ symbol, quantity, avgCost, marketValue, unrealizedPnL }]
getBrokerBalances()   → { totalEquity, buyingPowerUSD, buyingPowerCAD, ... }
getBrokerOrders()     → [{ orderId, symbol, action, qty, status, filledAt }]
```

### New Python script: `investment_screener/backend/py_services/fetch_broker_data.py`
Thin Python wrapper around the Node broker_data.js module (same pattern as `place_order.py`):

```bash
# Fetch all accounts
python3 investment_screener/backend/py_services/fetch_broker_data.py --accounts

# Fetch positions for active account
python3 investment_screener/backend/py_services/fetch_broker_data.py --positions

# Fetch full portfolio snapshot
python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot
```

Output: JSON to stdout (same schema as `portfolio.json`).

### Abstraction layer interface (canonical functions)
All consumers call these — the source is resolved underneath:

```
getAccounts(source?)   → [{ accountId, accountType, currency }]
getPositions(source?)  → [{ symbol, quantity, avgCost, marketValue, unrealizedPnL }]
getBalances(source?)   → { totalEquity, buyingPowerUSD, buyingPowerCAD }
getOrders(source?)     → [{ orderId, symbol, action, qty, status }]
getPortfolio(source?)  → merged snapshot (same schema as portfolio.json)
```

`source` is one of `'tv' | 'questrade' | 'auto' | 'compare'`.

### Data source resolution order (auto mode)
```
1. TradingView CDP (primary — works for any connected broker)
2. Questrade REST API (optional fallback — .questrade_cache exists + TV unreachable)
3. portfolio.json cache (final fallback — stale but always available)
```

### Cross-validation mode (`--source compare`)
Runs both TV and Questrade in parallel, diffs the results field-by-field:
```
python3 fetch_broker_data.py --positions --source compare
```
Output shows matched rows (✓), quantity mismatches (⚠ TV:16 QT:15), and symbols only in one source.

**This is the primary validation tool during development** — run compare, fix discrepancies in the TV scraper until it matches Questrade, then TV becomes the trusted primary. Questrade can be dropped from required setup once compare passes.

The backend's `QuestradeSyncService.ts` gets refactored into a generic `BrokerSyncService.ts` that delegates to whichever source is available.

## Implementation Plan

### Phase 1 — CDP broker_data.js scraper ✅ COMPLETE
- [x] Audit TradingView's broker panel DOM for positions table (class selectors, row structure)
- [x] Implement `getPositions()` — scrape the positions table rows, parse symbol/qty/cost
- [x] Implement `getBalances()` — reads Account Summary tab with CAD/USD columns
- [x] Implement `getAccounts()` — MutationObserver-based account dropdown enumeration
- [x] Implement `getOrders()` — scrape open orders list
- [x] Validated: 31/31 positions matched against Questrade, 0 qty mismatches

### Phase 2 — Python wrapper script ✅ COMPLETE
- [x] `fetch_broker_data.py` with `--accounts`, `--positions`, `--balances`, `--orders`, `--snapshot` flags
- [x] `--source tv|questrade|auto|compare` flag
- [x] `--compare` aggregates all TV accounts and diffs against portfolio.json
- [x] `--snapshot` writes portfolio_tv.json (safe; does not overwrite portfolio.json)
- [x] `--promote` flag to promote TV snapshot to portfolio.json

### Phase 3 — Backend integration ✅ COMPLETE
- [x] Created `BrokerSyncService.ts` — TV sync, merge, and auto source resolution
- [x] `POST /api/portfolio/sync-tv` — TV snapshot + diff; returns merged array for review
- [x] `POST /api/portfolio/sync-tv/promote` — writes merged array to portfolio.json
- [x] `POST /api/portfolio/sync` — auto source (TV → Questrade → cache)
- [x] `GET /api/portfolio` now returns `dataSource` field (tradingview-cdp | questrade | cache)

### Phase 4 — New skill `/tv-portfolio-sync` ✅ COMPLETE
- [x] Skill created at `plugins/portfolio-advisor/skills/tv-portfolio-sync/SKILL.md`
- [x] HITL diff display before writing (added/removed/changed format)
- [x] Added to skill tables in CLAUDE.md, GEMINI.md, copilot-instructions.md
- [x] Works without Questrade credentials

### Phase 5 — Questrade becomes optional ✅ COMPLETE
- [x] `run_investment_toolkit.py` — softened Questrade warning; notes TV sync works without it
- [x] `toolkit-onboarding-guide.md` — TV setup is now Phase 3 (primary); Questrade is Phase 4 (optional)
- [x] All skill tables updated: `/setup-questrade` noted as optional

## Acceptance Criteria ✅
- [x] `fetch_broker_data.py --snapshot` produces valid snapshot from TradingView DOM alone
- [x] Backend `/api/portfolio/sync` and `/api/portfolio/sync-tv` endpoints wired
- [x] `dataSource` field in `/api/portfolio` response
- [x] Questrade path still available when `.questrade_cache` is present (no regression)
- [x] `/tv-portfolio-sync` skill documented and registered

## Key Files
| File | Action |
|------|--------|
| `plugins/tradingview/node/core/broker_data.js` | **CREATE** — CDP broker panel scraper |
| `investment_screener/backend/py_services/fetch_broker_data.py` | **CREATE** — Python wrapper |
| `investment_screener/backend/src/services/BrokerSyncService.ts` | **CREATE** — unified sync service |
| `investment_screener/backend/src/services/QuestradeSyncService.ts` | **REFACTOR** — register as optional provider |
| `.agents/skills/place-order/SKILL.md` or new `/tv-portfolio-sync` | **CREATE** — new sync skill |

## Notes
- DOM selectors for TradingView's positions table will need live inspection (CDP `Runtime.evaluate`)
- TradingView's broker panel uses the same hashed CSS class convention as the order dialog
- The `broker_data.js` scraper should re-use `connect()` / `evaluate()` from `connection.js` (same pattern as `trading.js`)
- Questrade account IDs visible in TradingView's account dropdown can be used to cross-reference the Questrade REST API if both sources are available
