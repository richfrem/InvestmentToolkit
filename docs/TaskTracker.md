# Task Tracker

This file maps each user requirement (from `docs/UserRequirements.md`) to its implementation status. Use this tracker to monitor progress and ensure all requirements are actionable.

**Note:** When adding a new requirement to `UserRequirements.md`, always update this Task Tracker to reflect the change.

## Task List

- [x] **UR1:** User can trigger holdings fetch from Questrade API via "Fetch Holdings" button.
- [x] **UR2:** Holdings displayed in a simple table with columns: Symbol, Quantity, Book Value, Market Value.
- [x] **UR3:** Data stored in local .ts file (V1) for quick access.
- [ ] **UR4:** Manual OAuth authentication via browser popup/modal.
- [x] **UR5:** Automated refresh token management: app updates .env with new refresh token after each successful token exchange.
- [ ] **UR6:** User can view and manage refresh token status in the UI (future).
- [x] **UR7:** API error handling and user feedback for token issues.
- [ ] **UR8:** Support for spreadsheet export (V2).
- [ ] **UR9:** Rebalancing calculator UI (V3).
- [ ] **UR10:** Holdings visualization with charts (V4).
- [x] **UR11:** Account-level inventory: For each account, display stocks, ETFs, and cash with book value, market value, number of shares, gain/loss $ and % on each holding.
- [ ] **UR12:** Portfolio-thesis alignment: Compare actual holdings against investment thesis pillars and target allocations.
- [ ] **UR13:** Map holdings to thesis pillars, highlight gaps, overweights, underweights, and thesis breakers.
- [ ] **UR14:** Export inventory and alignment analysis to spreadsheet or PDF.
- [x] **UR15:** Incremental, modular development—features can be built and refined step by step.
- [x] **UR16:** Secure: No password storage, .env for secrets, Husky pre-commit scans, and OAuth2 refresh token management as documented in ADR 001.
- [x] **UR17:** Responsive UI with modern design (shadcn/ui, Tailwind).
- [x] **UR18:** Local-first: Holdings data is preserved in a local TypeScript file in V1 for quick access and reliability. SQLite will be used for local caching and persistence in future versions (V2+). No external DB in V1.
- [x] **UR19:** Incremental feature rollout with clear versioning.
- [x] **UR20:** All data contracts (TypeScript interfaces/types) for positions, holdings, and related entities must be aligned with the official Questrade API schemas for consistency and reliability. See ADR 006 (adrs/006-data-contracts-aligned-with-questrade.md) for details. When updating or adding new contracts, always reference the Questrade API documentation and update ADR 006 if the approach changes.
- [x] **UR21:** Ability to export all in-memory account, holdings, positions, balances, and orders data to a file or string for prompt/AI analysis, spreadsheet export, or external review. This enables easy integration with LLMs and other analysis tools.
- [x] **UR31:** Comprehensive logging system with environment-controlled debugging. A centralized logger utility (`backend/src/utils/logger.ts`) provides structured logging with multiple levels (debug, info, success, warn, error) and specialized loggers for different components (api, data, questrade, portfolio). Debug logging is controlled by the `DEBUG_LOGGING=true` environment variable to keep production logs clean while enabling detailed debugging when needed.
- [x] **UR32:** Data mapping from source to destination schemas must be explicit, documented, and validated. All data transformations between Questrade API responses and internal data structures (including portfolio master data, holdings aggregation, and pillar mappings) must include clear field mappings, type conversions, and validation rules. Schema transformations should be versioned and tested to ensure data integrity across the pipeline.
- [x] **UR22:** LLM-Driven Portfolio Analysis Workflow. Implemented server-side AI integration (`backend/src/services/aiService.ts`), prompt generator (`backend/src/utils/portfolioUtils.ts`), and API endpoints (`/api/run-analysis`, `/api/save-thesis`, `/api/save-prompt`). Frontend Strategy AI page added (`frontend/src/pages/StrategyAIPage.tsx`) with save/run UX and markdown rendering. End-to-end verification completed (backend + frontend + OpenAI).
- [~] **UR23:** Portfolio Alignment Table Generation Script. Script exists (`scripts/generate_portfolio_alignment_table.ts`) and `update-portfolio-data` API implemented; basic alignment output flows to `TargetPortfolio/portfolio_master_data.json`. Status: in-progress — needs formatting/export to a dedicated markdown report (`TargetPortfolio/portfolio_thesis_alignment_report.md`) and review for LLM-readiness.

---

**Reminder:** Always update this file when adding, removing, or changing requirements in `UserRequirements.md`.
