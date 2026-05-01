# Acceptance Criteria: Run Screener

## Functional Requirements
- Must execute `python3 run_investment_toolkit.py` from the root.
- Must monitor logs for successful startup (port 3001 and 5173).
- Must report URLs to the user.

## Quality Standards
- Inform user how to stop the processes.
- Handle common startup failures (port conflicts) gracefully.
