---
name: questrade-sync-portfolio
plugin: questrade
description: Directly syncs Questrade account balances, holdings, and cash splits into domain_model.sqlite. Trigger on /questrade-sync-portfolio or "sync questrade portfolio".
allowed-tools: Bash, Read, Write
---

# Questrade Sync Portfolio

Directly queries Questrade MCP balances and positions tools to synchronize holdings and cash into SQLite domain model.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **Scope boundaries**: Syncs holdings, quantities, cash splits, and exchange rates; does not update market prices.
- **Account resolution**: Canonical account identifiers (`TFSA`, `RRSP`, `CASH`) are mapped automatically by `questrade_sync.py`.
- **Atomic sync**: Stale positions no longer present in the Questrade account snapshot are cleared automatically.

## Quick start

Execute full portfolio ingestion from Questrade:

```bash
python3 plugins/questrade/skills/questrade-sync-portfolio/scripts/questrade_sync.py --help
```

Use `--dry-run` to preview changes without committing to SQLite.

## Workflow

1. **Query MCP Account Data**:
   - Call MCP tool `List Accounts` to enumerate active accounts.
   - For each account, call `Get Balances` and `Get Positions`.
2. **Stage Intermediate Payload**:
   Construct payload at `temp/questrade_sync_payload.json` containing `accounts`, `balances`, and `positions`.
3. **Execute Persistence Script**:
   ```bash
   python3 plugins/questrade/skills/questrade-sync-portfolio/scripts/questrade_sync.py --payload temp/questrade_sync_payload.json
   ```
4. **Trigger Refresh & Invariant Check**:
   - Run `python3 investment_screener/backend/py_services/verify_portfolio_invariants.py`.
   - Remove temporary JSON payload and display sync summary.

## Verification

- Confirm portfolio invariants match via `verify_portfolio_invariants.py`.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade Tool Schemas](references/questrade-tool-schemas.md): Schema reference for `list_accounts`, `get_balances`, and `get_positions`.
