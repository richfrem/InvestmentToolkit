# Questrade MCP — Live Tool Schemas (Canonical)

Ground truth for the actual Questrade MCP tool signatures and response shapes, captured from live sessions — not the marketing tool matrix in `questrade-mcp-ai-integration.md`. When a live call reveals a mismatch between this file and reality, fix this file first (single source), then any SKILL.md that quoted it goes stale until the next read — SKILL.md files should describe *workflow*, not re-document parameter names.

All accounts and orders are addressed by `accountId` (uuid) from `list_accounts` / `orderId` (uuid) from `get_order_history`. There is no `symbol`-only or account-number addressing anywhere in this API.

## Read tools

### `list_accounts()`
No params. Returns `[{id, name, productType, supportTrading}]`. `supportTrading` is `true` only for self-directed (`SD`) accounts.

### `get_balances(accountId)`
Returns `{accountId, balances: {maxBuyingPower, totalBuyingPower, buyingPower, totalEquity, marketValue, cash}, profit: {dayPnl, closedPnl, openPnl}}`. Each balance/profit leaf is `{cad, usd, combinedCad, combinedUsd}` as formatted currency strings (e.g. `"$131.08"`), not raw numbers.

### `get_positions(accountId)`
Returns `[{id, instrument, qty, side, avgPrice}]` — flat array, `[]` if no holdings. **`instrument` holds the symbol, not `symbol`.** No current price, market value, or unrealized P&L per row — pull those from `get_balances` (account-level) or `get_quotes` (per-symbol).

### `get_account_activities(accountId, fromDate?, toDate?, page?, transactionTypes?)`
`fromDate`/`toDate` are plain `YYYY-MM-DD` (not ISO timestamps). `transactionTypes` is an array from the enum: `Trades | Interest | Other | Dividends | FX conversion | Dividend reinvestment | Corporate actions | Transfers | Withdrawals | Deposits | Fees and rebates`. Returns `{accountId, activities: [...], metadata: {totalCount, totalPages, count, currentPage}}`, paged 20/page. **Unfiltered results are dominated by `Trades` noise** (observed 143 trades vs 12 real cash-flow events in one 90-day window) — always pass `transactionTypes` scoped to intent rather than fetching everything and filtering client-side.

### `search_symbols(query, hasOptions?, limit?)`
Returns matches with security UUID, exchange, market cap, industry. Use the UUID for `get_quotes(securityUuids=[...])` when you need Greeks/IV (option contracts); use `get_quotes(symbols=[...])` for plain equity quotes without a prior search.

### `get_quotes(symbols? | securityUuids?)`
Up to 20 of either. Equities get bid/ask/last + fundamentals; option contracts additionally get Greeks, IV, ITM probability.

## Order tools (HITL-gated — Rule #17)

### `preview_order_instruction(accountId, instrument, qty, side, type, limitPrice?, stopPrice?, duration?)`
- `side`: `"buy" | "sell"`. `type`: `"market" | "limit" | "stop" | "stoplimit"`. `duration`: `"day" | "gtc"`, **defaults `"day"`**.
- Side-effect-free — always call before `create_order_instruction`.
- Returns `{confirmId, sections: [...], warnings: [...], errors: [...], estimatedTotal, isFractionalSharesEligible}`. Check `errors` is empty and read `warnings` before presenting to the user.
- Fractional `qty` is only accepted for fractional-eligible tickers on a market order with Day duration — `isFractionalSharesEligible` tells you which.

### `create_order_instruction(operation, accountId, instrument?, qty?, side?, type?, limitPrice?, stopPrice?, duration?, orderId?)`
- `operation`: `"create" | "modify" | "cancel"` (required). `create` needs `side`/`type`/`qty`/`instrument`; `modify` needs `orderId`+`qty`/`instrument` (side/type are immutable — cannot flip buy↔sell or change order type on an existing order); `cancel` needs only `orderId`.
- **This call blocks on the user's phone.** It sends a push-to-approve request to an enrolled trusted device (QuestMobile / EdgeMobile) and waits for approve/reject/timeout. **There is no browser or desktop approval flow** — a user "on the computer" still needs their phone.
- If no trusted device is enrolled, the call errors immediately: *"Could not send an approval request to your mobile device..."* — this is not terminal. Tell the user to open the mobile app and enroll a device, then **retry the identical call** once they confirm it's open. Confirmed working recovery path (2026-08-26).
- Success: `{"status":"placed","orderId":"<uuid>"}` (or `"modified"`/`"cancelled"` per operation). Report the `orderId` back as live confirmation.
- **Day is the default duration** (pitfall #22) — GTC must be requested explicitly via `duration:"gtc"` on `create`, since `modify` cannot change duration afterward. Always state Day-vs-GTC in the final confirmation to the user.

## Account disambiguation (not an API fact, but load-bearing)

None of these tools accept a friendly account label (`TFSA`, `RRSP`) — only `accountId`. When a ticker is held in more than one account, or the user didn't name one, **ask explicitly** which account before calling `preview_order_instruction` — don't infer from conversation context. Cross-reference `get_positions` per account to show existing holdings as decision context. Per the project's capital sourcing rules, TFSA is the primary/larger account and RRSP mirrors it at roughly 1/3 the share count.
