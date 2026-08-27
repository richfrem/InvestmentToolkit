---
name: questrade-refresh-prices
description: "Refreshes live market prices for held positions into domain_model.sqlite via Questrade get_quotes."
argument-hint: "[--dry-run]"
allowed-tools: Bash, Read
---

# Refresh Prices

## Purpose
Fetches live quotes for currently-held, USD-denominated, non-cash investments via Questrade's get_quotes MCP tool and writes them into investment_price — an optional, user-triggered augment to the existing TradingView/yfinance pricing baseline (Rule #20), fully separate from questrade-sync-portfolio's holdings/balances sync.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Schema Reference
See `references/questrade-tool-schemas.md` (get_quotes section) for exact tool param names and response shapes — do not re-derive or guess these from memory.

## Skill-Specific Behavior
- **Never runs automatically.** This skill is a fully separate, user-triggered action from `questrade-sync-portfolio` — a holdings sync never implicitly refreshes prices, and this skill never implicitly re-syncs holdings.
- **Excludes non-tradeable cash rows** (`CASH_USD`, `asset_class == "CASH"`) from any quote request — `get_quotes` would never resolve a synthetic symbol like that anyway.
- **Excludes non-USD-denominated investments** (e.g. `DLR.TO`, `PSU-U.TO`) from any quote request, and `questrade_price_refresh.py` independently re-checks each quote's own `currency` field at write time as a second guard. `get_positions` carries no currency signal, so this domain model cannot yet safely re-price a non-USD holding from a Questrade quote — skipped symbols are reported, not silently dropped.
- **Batches at 20 symbols per `get_quotes` call** (Questrade's per-call cap). A ~24-symbol portfolio needs 2 calls.

## Workflow
1. **Determine eligible symbols**: run `python3 scripts/questrade_price_refresh.py --payload <any-empty-or-prior-payload> --dry-run` is not sufficient for symbol discovery — instead query `investment`/`account_investment` directly (`asset_class != 'CASH' AND currency = 'USD'`), or simply reuse the current holdings list from a recent `questrade-sync-portfolio` or `questrade-get-positions` run, deduplicated across accounts.
2. **Batch and fetch quotes**: split the symbol list into groups of ≤20, call MCP tool `Get Quotes(symbols=[...])` once per batch.
3. **Stage the payload**: merge all batch responses into one JSON file at `temp/questrade_price_refresh_payload.json`:
   ```json
   { "quotes": { "BTDR": { "symbol": "BTDR", "currency": "USD", "lastPrice": 11.845, ... }, ... } }
   ```
4. **Execute the persistence script**:
   ```bash
   python3 plugins/questrade/skills/questrade-refresh-prices/scripts/questrade_price_refresh.py --payload temp/questrade_price_refresh_payload.json
   ```
5. **Clean up & report**: remove the temporary payload file, then display a summary — symbols updated, symbols skipped (and why: non-USD currency, CASH asset_class, or no usable price in the quote response).

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine `references/questrade-tool-schemas.md` (the canonical, hub-and-spoke source) first — not this file — then this file's `## Skill-Specific Behavior` section only for details unique to this skill's workflow.
