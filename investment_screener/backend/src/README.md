# Express Backend Source Directory (`backend/src/`)

Welcome to the backend service core. This directory houses the TypeScript Express server, routing modules, orchestrator services, and utility endpoints supporting the **InvestmentToolkit** workstation.

---

## 📂 Directory Layout

```
src/
├── index.ts                 # Express Server Entry Point (Bootstrap & Configuration)
├── middleware/              # Express Request Gateways
│   └── localAuth.ts         # Bearer token validator (.runtime/api-token)
├── routes/                  # Express REST Router Mounts
│   ├── dailybrief.ts        # GET /api/daily-brief/* endpoints
│   ├── docs.ts              # GET /api/docs/* and GET /api/research/*
│   ├── portfolio.ts         # GET/POST /api/portfolio/* and syncs
│   ├── projections.ts       # GET/POST/DELETE /api/projections/*
│   ├── screener.ts          # Watchlist and all-holdings screener aggregates
│   ├── stock.ts             # Stock lookups, metrics, and quotes
│   ├── theses.ts            # Thesis CRUD, pillars, and rebalancer health check
│   ├── thirteenf.ts         # SEC 13F parsed filings and diffs
│   └── trading.ts           # Order placement sessions (CDP) & trade log CRUD
├── services/                # Orchestrators and Analytical Coordinators
│   ├── AnalysisContextBuilder.ts  # Aggregates stock details for AI analysis
│   ├── BrokerSyncService.ts # TV CDP waterfall sync orchestrator
│   ├── GeminiService.ts     # Client interface for Google Gemini models
│   ├── ProjectionService.ts # DCF projection file CRUD & atomic locks
│   ├── ThesisService.ts     # Health checks, optimization prompts, and reviews
│   ├── ValuationService.ts  # Freshness cached AI valuation analyst
│   ├── WatchlistService.ts  # Watchlist array database CRUD & locking
│   └── bridge.ts            # Subprocess bridge executing python analytical scripts
├── utils/                   # Shared type definitions and conversion utilities
│   ├── helpers.ts           # TCP checks, currency fetchers, and script queries
│   ├── paths.ts             # Directory mapping constants
│   ├── portfolioSnapshot.ts # Cash aggregators and broker total managers
│   ├── stockLookup.ts       # Fuzzy company name search resolver
│   ├── strategyAllocation.ts# Holding categorizer by strategy/pillar
│   ├── tickerAliases.ts     # Normalizer maps for broker symbols
│   └── zod-schemas.ts       # Central zod validation schemas (E2/Rebalancer schemas)
```

---

## ⚡ Key Architecture Patterns

### 1. The Python Bridge (`services/bridge.ts`)
The Node.js backend handles HTTP connections and API routing, but offloads complex analytical calculations (TWR calculations, financial scraping, TradingView CDP control) to Python scripts located in `py_services/`.
- **Deduplication**: Simultaneous identical requests await the same in-flight subprocess Promise.
- **Resilience**: Script timeouts fall back to returning the last successfully cached result with a `stale: true` flag.

### 2. Multi-Account Broker Snapshot Waterfall
The `BrokerSyncService.ts` queries the active TradingView CDP session center (listening on port 9222) to fetch live positions. If TradingView is unreachable, it defaults back to local caching. Authoritative equity totals are preserved across operations to prevent pricing refreshes from resetting broker balance records.

### 3. Zod-Driven Contract Validation
All core files (`portfolio.json`, `target-portfolio.json`, projections, etc.) are validated at both the route and database layers against schemas defined in [`zod-schemas.ts`](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/src/utils/zod-schemas.ts). This ensures type safety and structure consistency across the TypeScript API and Python sub-processes.

---

## 📜 Coding Conventions

Before adding code or endpoints in this directory, review [`.agent/rules/coding-conventions.md`](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/.agent/rules/coding-conventions.md). Remember to:
- Begin every file with a purpose header specifying **Key Input/Output Dependencies** and a complete **Functions/Routes Index**.
- Ensure all function signatures specify complete type annotations.
- Run `npm run build -w backend` to verify compiler compliance before submitting.
