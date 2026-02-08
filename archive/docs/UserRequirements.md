# User Requirements

**NOTE:** Ensure all new requirements are captured in the `./TaskTracker.md`

## Functional Requirements
- **UR1:** User can trigger holdings fetch from Questrade API via "Fetch Holdings" button.
- **UR2:** Holdings displayed in a simple table with columns: Symbol, Quantity, Book Value, Market Value.
- **UR3:** Data stored in local .ts file (V1) for quick access.
- **UR4:** Manual OAuth authentication via browser popup/modal.
- **UR5:** Automated refresh token management: app updates .env with new refresh token after each successful token exchange.
- **UR6:** User can view and manage refresh token status in the UI (future).
- **UR7:** API error handling and user feedback for token issues.
- **UR8:** Support for spreadsheet export (V2).
- **UR9:** Rebalancing calculator UI (V3).
- **UR10:** Holdings visualization with charts (V4).
- **UR11:** Account-level inventory: For each account, display stocks, ETFs, and cash with book value, market value, number of shares, gain/loss $ and % on each holding.
- **UR12:** Portfolio-thesis alignment: Compare actual holdings against investment thesis pillars and target allocations.
- **UR13:** Map holdings to thesis pillars, highlight gaps, overweights, underweights, and thesis breakers.
- **UR14:** Export inventory and alignment analysis to spreadsheet or PDF.
- **UR15:** Incremental, modular development—features can be built and refined step by step.

## Non-Functional Requirements
- **UR16:** Secure: No password storage, .env for secrets, Husky pre-commit scans, and OAuth2 refresh token management as documented in ADR 001.
- **UR17:** Responsive UI with modern design (shadcn/ui, Tailwind).
- **UR18:** Local-first: Holdings data is preserved in a local TypeScript file in V1 for quick access and reliability. SQLite will be used for local caching and persistence in future versions (V2+). No external DB in V1.
- **UR19:** Incremental feature rollout with clear versioning.
**UR20:** All data contracts (TypeScript interfaces/types) for positions, holdings, and related entities must be aligned with the official Questrade API schemas for consistency and reliability. See ADR 006 (adrs/006-data-contracts-aligned-with-questrade.md) for details. When updating or adding new contracts, always reference the Questrade API documentation and update ADR 006 if the approach changes.
- **UR31:** Comprehensive logging system with environment-controlled debugging. A centralized logger utility (`backend/src/utils/logger.ts`) provides structured logging with multiple levels (debug, info, success, warn, error) and specialized loggers for different components (api, data, questrade, portfolio). Debug logging is controlled by the `DEBUG_LOGGING=true` environment variable to keep production logs clean while enabling detailed debugging when needed.
- **UR32:** Data mapping from source to destination schemas must be explicit, documented, and validated. All data transformations between Questrade API responses and internal data structures (including portfolio master data, holdings aggregation, and pillar mappings) must include clear field mappings, type conversions, and validation rules. Schema transformations should be versioned and tested to ensure data integrity across the pipeline.
  
**UR21:** Ability to export all in-memory account, holdings, positions, balances, and orders data to a file or string for prompt/AI analysis, spreadsheet export, or external review. This enables easy integration with LLMs and other analysis tools.
  
	Key Questrade API documentation for reference:
	- [Accounts Balances](https://www.questrade.com/api/documentation/rest-operations/account-calls/accounts-id-balances)
	- [Accounts](https://www.questrade.com/api/documentation/rest-operations/account-calls/accounts)
	- [Accounts Positions](https://www.questrade.com/api/documentation/rest-operations/account-calls/accounts-id-positions)
	- [Accounts Orders](https://www.questrade.com/api/documentation/rest-operations/account-calls/accounts-id-orders)
	- ...and other relevant endpoints as needed.

**UR22:** LLM-Driven Portfolio Analysis Workflow

*Goal:* Enable an LLM to analyze current portfolio/account data, compare it against the investment thesis, and recommend improvements.

*Requirements:*
1. **Data Access**
	- LLM must be able to read and process all relevant data files, including `exportedData.json` (latest portfolio snapshot), and any supporting markdown or code files.
	- Data export scripts must ensure `exportedData.json` is always up-to-date and complete.

2. **Thesis Integration**
	- LLM must be able to access and parse the investment thesis (`InvestmentThesis/twin_revolution_ASI_and_Sovereign_finance.md`).
	- Pillar definitions, target allocations, and sell discipline criteria must be extractable for analysis.

3. **Prompt-Based Analysis**
	- Provide a prompt template (e.g., `Prompts/portfolio_thesis_alignment_prompt.md`) that instructs the LLM to:
	  - Summarize current portfolio allocations and holdings.
	  - Compare actual allocations to thesis targets and pillar weightings.
	  - Identify misalignments, over/underweights, and missing exposures.
	  - Apply sell discipline and risk factor checks.
	  - Recommend specific adjustments (e.g., rebalance, add/remove positions, adjust weights).

4. **Recommendations Output**
	- LLM should output a markdown report with:
	  - Portfolio summary table.
	  - Thesis alignment analysis.
	  - Actionable recommendations for improvement.
	  - Rationale for each recommendation (referencing thesis sections).

5. **Workflow Documentation**
	- Document the end-to-end workflow in `UserRequirements.md` and `TaskTracker.md`:
	  - How to export data.
	  - How to run the LLM analysis.
	  - How to interpret and act on recommendations.

**UR23:** Portfolio Alignment Table Generation Script

Create a script in `scripts/` (e.g., `generate_portfolio_alignment_table.ts`) that:
	- Reads `questrade-portfolio-app/backend/exportedData.json`
	- Aggregates holdings across all accounts (grand total shares, average value, % of total portfolio value per ticker/pillar)
	- Compares actual allocations to thesis target percentages
	- Highlights gaps, overweights, underweights, and thesis breakers
	- Outputs a markdown table to `TargetPortfolio/portfolio_thesis_alignment_report.md`
The LLM prompt will analyze this table, provide recommendations, and update target values/gaps as needed.

## LLM Prompt Usage for Portfolio-Thesis Alignment

**Goal:** Enable an LLM to analyze current portfolio/account data, compare it against the investment thesis, and recommend improvements.

**Requirements:**
1. **Data Access**
	- LLM must be able to read and process all relevant data files, including `exportedData.json` (latest portfolio snapshot), and any supporting markdown or code files.
	- Data export scripts must ensure `exportedData.json` is always up-to-date and complete.

2. **Thesis Integration**
	- LLM must be able to access and parse the investment thesis (`InvestmentThesis/twin_revolution_ASI_and_Sovereign_finance.md`).
	- Pillar definitions, target allocations, and sell discipline criteria must be extractable for analysis.

3. **Prompt-Based Analysis**
	- Provide a prompt template (e.g., `Prompts/portfolio_thesis_alignment_prompt.md`) that instructs the LLM to:
	  - Summarize current portfolio allocations and holdings.
	  - Compare actual allocations to thesis targets and pillar weightings.
	  - Identify misalignments, over/underweights, and missing exposures.
	  - Apply sell discipline and risk factor checks.
	  - Recommend specific adjustments (e.g., rebalance, add/remove positions, adjust weights).

4. **Recommendations Output**
	- LLM should output a markdown report with:
	  - Portfolio summary table.
	  - Thesis alignment analysis.
	  - Actionable recommendations for improvement.
	  - Rationale for each recommendation (referencing thesis sections).

5. **Workflow Documentation**
	- Document the end-to-end workflow in `UserRequirements.md` and `TaskTracker.md`:
	  - How to export data.
	  - How to run the LLM analysis.
	  - How to interpret and act on recommendations.

## Additional Requirements

**UR24:** Automated Backup & Version Control
- All critical data files, documentation, and ADRs should be versioned using git or an automated backup workflow. This ensures restore points are available and prevents accidental data loss.

**UR25:** Error Logging & Diagnostics
- Implement comprehensive error logging for backend and frontend operations. Logs should be easily accessible for debugging and include timestamps, error codes, and actionable messages.

**UR26:** Data Integrity Checks
- Add validation routines to ensure exported data (JSON, CSV, markdown) matches expected schema and is free of corruption or missing fields before analysis or export.

**UR27:** User-Driven Restore Workflow
- Provide a simple UI or CLI tool for restoring previous versions of documentation, ADRs, and data files from backups or git history.

**UR28:** Security Audit Trail
- Maintain an audit trail of all file operations (create, edit, delete, move) for sensitive data and documentation, with user attribution and timestamps.

**UR29:** Accessibility & Usability
- Ensure the UI and exported reports are accessible (WCAG compliance), with clear navigation, readable tables, and support for screen readers.

**UR30:** Modular Prompt Library
- Maintain a library of prompt templates for LLM analysis, portfolio review, and thesis alignment, versioned and documented for easy reuse and improvement.