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
Document the workflow and usage in `UserRequirements.md` and `TaskTracker.md`.