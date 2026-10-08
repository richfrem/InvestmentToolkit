---
name: questrade-sync-portfolio
plugin: questrade
description: Directly syncs Questrade account balances, holdings, cash splits and recently executed trades into domain_model.sqlite. Trigger on /questrade-sync-portfolio, "sync questrade portfolio" or "refresh my trades from questrade".
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

- **Sign-in first**: Questrade tools exist only after the owner signs in through a browser, and the sign-in does not carry over between sessions. If `List Accounts` is unavailable or fails, stop and follow `questrade-setup` (start the sign-in, give the owner the link, wait for them to finish) before staging any payload. Never substitute stale data for a failed sign-in.
- **Scope boundaries**: Syncs holdings, quantities, cash splits, and exchange rates; does not update market prices.
- **Account resolution**: Canonical account identifiers (`TFSA`, `RRSP`, `CASH`) are mapped automatically by `questrade_sync.py`.
- **Atomic sync**: Stale positions no longer present in the Questrade account snapshot are cleared automatically.
- **Trades with every sync**: Import executed trades in the same run so the Trade Log and the recommendations' recent-trade context match the new positions. Only executed trades are imported; open, cancelled and rejected orders are not.

## Quick start

Execute full portfolio ingestion from Questrade:

```bash
python3 plugins/questrade/skills/questrade-sync-portfolio/scripts/questrade_sync.py --help
```

Use `--dry-run` to preview changes without committing to SQLite.

## Workflow

1. **Query MCP Account Data**:
   - Call MCP tool `List Accounts` to enumerate active accounts; this also proves the session is signed in.
   - For each account, call `Get Balances` and `Get Positions`.
2. **Stage Intermediate Payload**:
   Construct payload at `temp/questrade_sync_payload.json` containing `accounts`, `balances`, and `positions`.
3. **Execute Persistence Script**:
   ```bash
   python3 plugins/questrade/skills/questrade-sync-portfolio/scripts/questrade_sync.py --payload temp/questrade_sync_payload.json
   ```
4. **Import Executed Trades**:
   - For each account call `Get Account Activities` with `transactionTypes=["Trades"]` for the last 30 days (page through `metadata.totalPages`).
   - Stage `temp/questrade_trades_payload.json` as `{"accounts": [...List Accounts rows...], "trades": [{"accountId", "symbol", "side": "buy"|"sell", "shares", "price", "date": "YYYY-MM-DD", "externalId"}]}` using the field mapping in the tool-schemas reference. Copy values exactly; never estimate a missing price, quantity or date.
   - Preview, then import:
   ```bash
   python3 plugins/questrade/skills/questrade-sync-portfolio/scripts/questrade_trades_import.py --payload temp/questrade_trades_payload.json --dry-run
   python3 plugins/questrade/skills/questrade-sync-portfolio/scripts/questrade_trades_import.py --payload temp/questrade_trades_payload.json --json
   ```
   - Exit code 2 means some trades were rejected: report each reason; do not edit values to force them through.
5. **Trigger Refresh & Invariant Check**:
   - Run `python3 investment_screener/backend/py_services/verify_portfolio_invariants.py`.
   - Remove temporary JSON payload and display sync summary.
   - Closing refresh: run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification

- Confirm portfolio invariants match via `verify_portfolio_invariants.py`.
- Confirm imported trades appear under the Trade Log page's Filled tab and that a re-run reports them as skipped, not imported again.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade Tool Schemas](references/questrade-tool-schemas.md): Schema reference for `list_accounts`, `get_balances`, `get_positions` and the trades import payload.
