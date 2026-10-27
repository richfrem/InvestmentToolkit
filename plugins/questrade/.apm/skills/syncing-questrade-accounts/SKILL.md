---
name: syncing-questrade-accounts
plugin: questrade
description: Connects the Questrade Brokerage MCP and reads or syncs account data. Covers MCP setup and sign-in diagnostics, balances and CAD/USD cash splits, open positions, cash-flow activities, syncing holdings and executed trades into domain_model.sqlite, and refreshing prices from Questrade quotes. Trigger on /questrade-setup, /questrade-get-balances, /questrade-get-positions, /questrade-activities, /questrade-sync-portfolio, /questrade-refresh-prices, "set up questrade mcp", "check questrade balances", "check questrade positions", "show my questrade dividend history", "sync questrade portfolio", "refresh my trades from questrade" or "refresh questrade prices".
allowed-tools: Bash, Read, Write
---

# Syncing Questrade Accounts

Reads Questrade account data through the official Questrade Brokerage MCP server and, in two modes, writes it into the toolkit's SQLite domain model. Order drafting, deposits and currency conversion live in the `trading-with-questrade` skill.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

Check the connection first: call `List Accounts`. If it returns account IDs, pick the mode below; if not, run the [setup mode](references/modes/setup.md).

## Workflow

1. Match the request to a mode in the table below and read its mode file.
2. Confirm a signed-in session with `List Accounts` (setup mode if it fails).
3. Follow the mode's workflow; read-only modes display results in chat and never touch the database.
4. For `sync-portfolio` and `refresh-prices`, preview with `--dry-run` before writing, then run the mode's verification.

## Constraints

- **Endpoint invariant**: the official MCP endpoint is `https://mcp.questrade.com/v1/brokerage/mcp`, `http` transport.
- **Credential isolation**: never request or persist raw Questrade API tokens in repository files; authentication is Questrade's OAuth browser flow, which only the owner can complete.
- **Sign-in first**: Questrade tools exist only after the owner signs in, and the sign-in does not carry over between sessions. Before any query, call `List Accounts`; if it is unavailable or fails, stop and follow the [setup mode](references/modes/setup.md). Never substitute stale data for a failed sign-in.
- **Tool boundary**: the MCP provides broker querying and order staging; analytics and database operations stay in the toolkit.
- **Read-only unless stated**: only `sync-portfolio` and `refresh-prices` write to the database.
- **Optional source**: TradingView is the default broker source. Use Questrade only when `python3 investment_screener/backend/py_services/broker_sources.py --json` lists `questrade` as available and the owner chose it for this refresh; otherwise run `/tv-portfolio-sync`.

## Modes

Read the mode file before acting. Paths starting with `scripts/` are relative to this skill's folder.

| Mode | Trigger | Writes to DB | What it does |
|---|---|---|---|
| [setup](references/modes/setup.md) | `/questrade-setup` | no | Adds the MCP server, runs the sign-in handshake, verifies with `List Accounts`, records `QUESTRADE_ENABLED` |
| [balances](references/modes/balances.md) | `/questrade-get-balances` | no | Equity, cash CAD/USD, buying power per account, shown in chat |
| [positions](references/modes/positions.md) | `/questrade-get-positions` | no | Open securities, quantity and average entry price |
| [activities](references/modes/activities.md) | `/questrade-activities` | no | Dividends, interest, deposits, withdrawals and trades over a date window |
| [sync-portfolio](references/modes/sync-portfolio.md) | `/questrade-sync-portfolio` | yes | Holdings, cash splits, exchange rate and executed trades into `domain_model.sqlite`, then re-baselines targets |
| [refresh-prices](references/modes/refresh-prices.md) | `/questrade-refresh-prices` | yes | Live quotes for USD holdings (or the full watchlist) into `investment_price` |

## Scripts

- `scripts/questrade_sync.py`: holdings, balances and exchange-rate ingestion (`--payload`, `--dry-run`).
- `scripts/questrade_trades_import.py`: executed-trade import (`--payload`, `--dry-run`, `--json`; exit code 2 means some trades were rejected).
- `scripts/questrade_price_refresh.py`: price persistence (`--payload`, `--full-watchlist`).
- Tests: `tests/` (run with `python3 -m pytest tests` from this folder).

## Verification

- Setup: `List Accounts` returns active account IDs.
- Sync: `python3 investment_screener/backend/py_services/verify_portfolio_invariants.py` passes; imported trades appear under the Trade Log page's Filled tab and a re-run reports them as skipped.
- Prices: `investment_price` rows are updated.
- Routing cases for every mode are in `evals/evals.json`.

## References

- [Questrade Tool Schemas](references/questrade-tool-schemas.md): parameter shapes, return schemas and error codes for every MCP tool, plus the trades import payload.
- [Questrade MCP Integration](references/questrade-mcp-ai-integration.md): multi-environment integration and transport architecture.
- [Evolution log](references/evolution-log.md): append-only history of changes to these skills.
- The `trading-with-questrade` skill: order drafting, deposits and CAD/USD conversion.
