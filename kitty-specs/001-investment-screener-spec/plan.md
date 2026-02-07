# Implementation Plan: [FEATURE]
*Path: [templates/plan-template.md](templates/plan-template.md)*


**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/kitty-specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/specify_cli/missions/software-dev/command-templates/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
# Implementation Plan - Investment Screener

## Summary
Build an investment analysis tool focused on valuation modeling. Users input growth/margin assumptions across Bull/Base/Bear scenarios, and the tool calculates 5-year price targets and CAGRs using the formula: `(Revenue * (1+g)^5 * Margin * PE) / Future Shares`. V1 uses `yfinance` for all data; Questrade integration deferred to V2.

**Branch**: `001-investment-screener-spec`
**Date**: 2026-02-07
**Spec**: [spec.md](./spec.md)

## Goal Description
Build a "Luxury Dark Mode" Investment Screener and Valuation Modeler.
**V1 Focus**: Core "Valuation Modeler" and "Expert Metrics" dashboard using `yfinance` data. Questrade and complex comparative screening are deferred to V2 to ensure a robust, high-quality MVP.

## Technical Context
**Language/Version**: Node.js 18+, Python 3.11+, React 19
**Primary Dependencies**: Express, `yfinance`, Recharts, Tailwind CSS
**Storage**: `localStorage` (Recently Analyzed list), no DB required for V1
**Testing**: Jest (frontend), Mocha (backend), pytest (Python bridge)
**Target Platform**: Local development (macOS/Linux/Windows via `startup.sh`)
**Project Type**: Web (Frontend + Backend)
**Performance Goals**: Dashboard load < 2s, model calc < 100ms
**Constraints**: `yfinance` rate limits, Questrade 1 req/sec (future)

## Project Structure
### Option 2: Web Application (Frontend + Backend)
```
tools/investment-screener/
├── backend/
│   ├── src/
│   │   ├── index.ts          # Express server
│   │   ├── services/
│   │   │   └── bridge.ts     # Python bridge (child_process)
│   │   └── routes/
│   │       └── api.ts        # /api/stock/:ticker endpoint
│   ├── py_services/
│   │   └── fetch_financials.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── ValuationModeler.tsx
│   │   │   └── Charts/
│   │   │       ├── FundamentalChart.tsx
│   │   │       └── RuleOf40Chart.tsx
│   │   └── services/
│   │       └── api.ts        # Fetch wrapper
│   └── tests/
├── startup.sh
├── .env.example (for tool-specific vars)
├── package.json (root workspace)
└── tailwind.config.js

**Note**: Questrade credentials (specifically `QUESTRADE_REFRESH_TOKEN`) should be sourced from `tools/archive/QuestTradePortfolioViewer/.env` OR the user's shell environment (checked via `.zshrc`). The startup script should verify this.
```

## Verification Plan

### Automated Tests
*   `backend`: Unit tests for `bridge.ts` to ensure it parses Python JSON correctly.
*   `py_services`: Test `fetch_financials.py` with known tickers (AAPL, PLTR) to verify schema.

### Manual Verification
1.  **Search Flow**: Search "PLTR", verify data loads < 3s.
2.  **Valuation Logical Check**:
    *   Set Growth=0%, Margin=Same, PE=Same, Shares=Same.
    *   Verify Target Price ~= Current Price (sanity check).
3.  **Persistence**: Refresh page, verify "PLTR" is in "Recently Analyzed".
4.  **Math Check**: Verify calculation logic with test case:
    *   **Inputs**: Rev=$400B, Growth=10%, Margin=25%, PE=30x, Shares=16B, ShareChg=-2%.
    *   **Formula**: `(400 * 1.1^5 * 0.25 * 30) / (16 * 0.98^5)`
    *   **Expected**: Target Price ~$320
    *   **Pass Criteria**: UI displays Target Price within $315-$325 range.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **No new third-party services**: Uses existing `yfinance` and optional Questrade API.
- [x] **No authentication required for V1**: Questrade deferred to V2/optional.
- [x] **Single startup script**: `startup.sh` provided for easy launch.
- [ ] **Cross-platform testing**: Verify on macOS/Linux/Windows (Task created).

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```
kitty-specs/[###-feature]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
## Proposed Changes

### [NEW] Backend Components
- **`backend/src/index.ts`**: Express server with CORS, error handling.
- **`backend/src/services/bridge.ts`**: Spawns Python via `child_process.spawn()`.
- **`backend/py_services/fetch_financials.py`**:
  - Fetch via `yfinance.Ticker(symbol)`.
  - Calculate Piotroski (9 metrics from financials/balance sheet).
  - Calculate Rule of 40 (Revenue Growth % + EBITDA Margin %).
  - Return JSON: `{metrics: {...}, historicals: {...}, info: {...}}`.

### [NEW] Frontend Components
- **`frontend/src/App.tsx`**: Main layout with Luxury Dark theme (bg-slate-950, accent-amber-500).
- **`frontend/src/components/Dashboard.tsx`**: Search + Expert Metrics panel.
- **`frontend/src/components/ValuationModeler.tsx`**: 3-tab UI (Bear/Base/Bull) with sliders.
- **`frontend/src/components/Charts/FundamentalChart.tsx`**: Recharts LineChart for Rev/Income.
- **`tailwind.config.js`**: Custom theme extending dark mode.

## Schema Changes
N/A (No database)

## Structure Decision
**Structure Decision**: Web application structure (Option 2) selected. Monorepo with separate `backend/` and `frontend/` directories under `tools/investment-screener/`. Shared root `package.json` for workspace management. Python bridge isolated in `backend/py_services/` for easy swap to alternative data providers.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |