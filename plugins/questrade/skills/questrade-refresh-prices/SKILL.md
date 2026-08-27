---
name: questrade-refresh-prices
description: "Refreshes live market prices into domain_model.sqlite via Questrade get_quotes — current holdings by default, or the full watchlist with --full-watchlist."
argument-hint: "[--dry-run] [--full-watchlist]"
allowed-tools: Bash, Read
---

# Refresh Prices

## Purpose
Fetches live quotes for USD-denominated, non-cash investments via Questrade's get_quotes MCP tool and writes them into investment_price — an optional, user-triggered augment to the existing TradingView/yfinance pricing baseline (Rule #20), fully separate from questrade-sync-portfolio's holdings/balances sync.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Schema Reference
See `references/questrade-tool-schemas.md` (get_quotes section) for exact tool param names and response shapes — do not re-derive or guess these from memory.

## Skill-Specific Behavior
- **Never runs automatically.** This skill is a fully separate, user-triggered action from `questrade-sync-portfolio` — a holdings sync never implicitly refreshes prices, and this skill never implicitly re-syncs holdings.
- **Excludes non-tradeable cash rows** (`CASH_USD`, `asset_class == "CASH"`) from any quote request — `get_quotes` would never resolve a synthetic symbol like that anyway.
- **Excludes non-USD-denominated investments** (e.g. `DLR.TO`, `PSU-U.TO`). The LIVE quote's own `currency` field is the authoritative check — not the stored `investment.currency` column, which is unreliable (this domain model hardcodes `currency='USD'` on every investment row today, including genuinely CAD-denominated tickers like `PSU-U.TO`). `questrade_price_refresh.py`'s `persist_quotes_to_prices()` checks `quote["currency"]`, not the stored value, so a mislabeled ticker's price is still caught and skipped rather than silently written under the wrong currency.
- **Batches at 20 symbols per `get_quotes` call** (Questrade's per-call cap).
- **Two scopes**: default is currently-held positions only (`account_investment.quantity > 0`); `--full-watchlist` widens this to every `investment` row with `is_watchlisted = 1` regardless of holding — `_select_investments_for_quote_refresh()` itself already queries the whole `investment` table (not joined to holdings), so no code change is needed to support this, only which symbol list the skill stages. A full watchlist run is typically 60-70+ symbols → 4 `get_quotes` calls.

## Workflow
1. **Determine eligible symbols** — pick the scope:
   - **Default (holdings only)**: `SELECT DISTINCT i.symbol FROM investment i JOIN account_investment ai ON ai.investment_id = i.investment_id WHERE i.asset_class != 'CASH' AND i.currency = 'USD' AND ai.quantity > 0`
   - **`--full-watchlist`**: `SELECT symbol FROM investment WHERE asset_class != 'CASH' AND currency = 'USD' AND is_watchlisted = 1`
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
