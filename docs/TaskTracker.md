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
- [ ] **UR22:** LLM-Driven Portfolio Analysis Workflow. Enable an LLM to analyze current portfolio/account data, compare it against the investment thesis, and recommend improvements. Includes data access, thesis integration, prompt-based analysis, recommendations output, and workflow documentation.
- [ ] **UR23:** Portfolio Alignment Table Generation Script. Create a script in scripts/ (e.g., generate_portfolio_alignment_table.ts) that reads exportedData.json, aggregates holdings across all accounts, compares actual allocations to thesis targets, highlights gaps/overweights/underweights/thesis breakers, and outputs a markdown table to TargetPortfolio/portfolio_thesis_alignment_report.md for LLM analysis and recommendations. Document workflow and usage in UserRequirements.md and TaskTracker.md.

---

**Reminder:** Always update this file when adding, removing, or changing requirements in `UserRequirements.md`.
