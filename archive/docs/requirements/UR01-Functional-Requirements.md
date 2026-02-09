# UR01: Functional Requirements

## Overview
Core application features that define the primary functionality of the Investment Toolkit.

## Requirements

### UR1: Holdings Data Fetch
**Description:** User can trigger holdings fetch from Questrade API via "Fetch Holdings" button.

**Acceptance Criteria:**
- Button is prominently displayed in the UI
- Clicking triggers API call to Questrade
- Loading state is shown during fetch
- Success/error feedback is provided

### UR2: Holdings Display
**Description:** Holdings displayed in a simple table with columns: Symbol, Quantity, Book Value, Market Value.

**Acceptance Criteria:**
- Table shows all current holdings
- Columns display required data fields
- Data is properly formatted (currency, numbers)
- Table is responsive and readable

### UR3: Local Data Storage (V1)
**Description:** Data stored in local .ts file for quick access.

**Acceptance Criteria:**
- Holdings data persists locally
- Fast access without API calls
- Data integrity maintained
- File-based storage for V1

### UR4: Authentication (Future)
**Description:** Manual OAuth authentication via browser popup/modal.

**Acceptance Criteria:**
- OAuth flow initiated from UI
- Secure token handling
- User-friendly authentication process
- Error handling for auth failures

### UR5: Token Management
**Description:** Automated refresh token management: app updates .env with new refresh token after each successful token exchange.

**Acceptance Criteria:**
- Tokens automatically refreshed
- .env file updated securely
- No manual token management required
- Secure token rotation

### UR6: Token Status UI (Future)
**Description:** User can view and manage refresh token status in the UI.

**Acceptance Criteria:**
- Token status visible in UI
- Token expiration warnings
- Manual token refresh option
- Clear status indicators

### UR7: Error Handling
**Description:** API error handling and user feedback for token issues.

**Acceptance Criteria:**
- Clear error messages for users
- Token-related errors handled gracefully
- Recovery suggestions provided
- No sensitive data exposed in errors

### UR8: Spreadsheet Export (V2)
**Description:** Support for spreadsheet export.

**Acceptance Criteria:**
- Export to common formats (CSV, Excel)
- All holdings data included
- Proper formatting preserved
- Download functionality

### UR9: Rebalancing Calculator (V3)
**Description:** Rebalancing calculator UI.

**Acceptance Criteria:**
- Target allocation input
- Current vs target comparison
- Rebalancing recommendations
- Trade calculations

### UR10: Charts and Visualization (V4)
**Description:** Holdings visualization with charts.

**Acceptance Criteria:**
- Interactive charts for holdings
- Multiple chart types (pie, bar, etc.)
- Data filtering and drill-down
- Responsive design

### UR11: Account-Level Inventory
**Description:** Account-level inventory: For each account, display stocks, ETFs, and cash with book value, market value, number of shares, gain/loss $ and % on each holding.

**Acceptance Criteria:**
- Multi-account support
- Detailed P&L calculations
- Account-specific views
- Comprehensive inventory display

### UR12: Portfolio-Thesis Alignment
**Description:** Portfolio-thesis alignment: Compare actual holdings against investment thesis pillars and target allocations.

**Acceptance Criteria:**
- Thesis pillar definitions loaded
- Actual vs target comparisons
- Gap analysis
- Alignment scoring

### UR13: Pillar Mapping
**Description:** Map holdings to thesis pillars, highlight gaps, overweights, underweights, and thesis breakers.

**Acceptance Criteria:**
- Automatic pillar classification
- Gap highlighting (visual indicators)
- Over/underweight identification
- Thesis breaker alerts

### UR14: Export Analysis
**Description:** Export inventory and alignment analysis to spreadsheet or PDF.

**Acceptance Criteria:**
- Comprehensive export formats
- Analysis data included
- Professional formatting
- Multiple export options

### UR15: Incremental Development
**Description:** Incremental, modular development—features can be built and refined step by step.

**Acceptance Criteria:**
- Modular architecture
- Feature flags for incremental rollout
- Backward compatibility
- Versioned releases

## Dependencies
- Questrade API access
- Local file system access
- Modern web browser support

### New AI Endpoints (addition)

- POST `/api/run-analysis` — Trigger LLM analysis of current portfolio with optional `{ thesis?: string }` body. Returns `{ success, analysis, error }`.
- POST `/api/save-thesis` — Persist `Thesis.md` to `TargetPortfolio/Thesis.md`.
- POST `/api/save-prompt` — Persist prompt template to `TargetPortfolio/Prompt.md`.
- GET `/api/file-content?file=...` — Read whitelisted files from `TargetPortfolio` (used by Strategy AI UI).

## Testing
- Unit tests for core functions
- Integration tests for API calls
- UI tests for user interactions
- End-to-end tests for workflows