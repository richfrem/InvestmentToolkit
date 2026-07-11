# Acceptance Criteria — ytd_return Skill

## Correct Execution Signals

### AC-01: Time-Weighted Rate of Return Linking
- **Condition**: User requests YTD return with deposits/withdrawals present
- **Pass**: Script computes intermediate sub-period returns, compounds them chronologically (TWRR linking), and prints the step-by-step math showing sub-period percentages.
- **Fail**: Script outputs simple net return as the only rate, or fails to compound chronologically.

### AC-02: Structural Output Integrity
- **Condition**: Script execution finishes successfully
- **Pass**: Outputs are written to a structured JSON file `investment_screener/backend/data/ytd_performance_report.json` matching the key names defined in `ytd_performance_report_template.json`.
- **Fail**: Report JSON is missing or structured differently from the templates schema.

### AC-03: Cash-Flow Date Matching
- **Condition**: cash_flows.json contains transaction records
- **Pass**: Transactions are sorted chronologically by date prior to calculating sub-periods.
- **Fail**: Transactions calculated in default/arbitrary JSON insertion order.
