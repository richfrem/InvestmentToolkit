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

### Data source resolution order (abstraction layer)
```
1. TradingView CDP (primary — works for any connected broker)
2. Questrade REST API (optional fallback — if .questrade_cache exists and TV unreachable)
3. portfolio.json cache (final fallback — stale but always available)
```

The backend's `QuestradeSyncService.ts` gets refactored into a generic `BrokerSyncService.ts` that delegates to whichever source is available.

## Implementation Plan

### Phase 1 — CDP broker_data.js scraper
- [ ] Audit TradingView's broker panel DOM for positions table (class selectors, row structure)
- [ ] Implement `getBrokerPositions()` — scrape the positions table rows, parse symbol/qty/cost
- [ ] Implement `getBrokerBalances()` — extend `getBrokerStatus()` from `trading.js` with totals
- [ ] Implement `getBrokerAccounts()` — parse account dropdown options
- [ ] Implement `getBrokerOrders()` — scrape open orders list if visible
- [ ] Unit-test output shape matches `portfolio.json` schema

### Phase 2 — Python wrapper script
- [ ] Create `fetch_broker_data.py` with `--accounts`, `--positions`, `--balances`, `--snapshot` flags
- [ ] `--snapshot` merges all sources and writes `portfolio.json` (replacing Questrade engine for this path)
- [ ] Add `--source tv|questrade|auto` flag for explicit override
- [ ] Error messages clearly guide user to open TradingView with broker connected if CDP unavailable

### Phase 3 — Backend integration
- [ ] Create `BrokerSyncService.ts` wrapping source resolution logic
- [ ] Expose `/api/portfolio/sync` endpoint that auto-picks source (TV CDP → Questrade → cache)
- [ ] Add `dataSource` field to portfolio API response so frontend can show "TV Live" vs "Questrade" vs "Cached"
- [ ] Update `QuestradeSyncService.ts` to register as an optional provider (not the only path)

### Phase 4 — New skill `/tv-portfolio-sync`
- [ ] Skill that runs `fetch_broker_data.py --snapshot` and shows diff vs current `portfolio.json`
- [ ] HITL: show what changed (new positions, closed positions, changed quantities) before writing
- [ ] Add to agent-quick-reference.md and skill tables in CLAUDE.md, GEMINI.md, copilot-instructions.md
- [ ] Available even without Questrade credentials

### Phase 5 — Questrade becomes optional
- [ ] Update startup script to skip Questrade seed check if `.questrade_cache` absent
- [ ] Update `/setup-questrade` messaging: "optional — only needed for direct API access; TV sync works without it"
- [ ] Update README/onboarding docs to present TradingView sync as the default path

## Acceptance Criteria
- [ ] `fetch_broker_data.py --snapshot` produces valid `portfolio.json` from TradingView DOM alone
- [ ] Backend `/api/portfolio/sync` works end-to-end with only TradingView running (no Questrade cache)
- [ ] Dashboard Heatmap, Table, and Summary views load correct data from the TV-sourced portfolio.json
- [ ] Questrade path still works when `.questrade_cache` is present (no regression)
- [ ] `dataSource` field in API response is visible in the Dashboard status badge

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
