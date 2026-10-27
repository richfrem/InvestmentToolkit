# Mode: refresh-prices (`/questrade-refresh-prices`)

Fetches live quotes for USD-denominated investments via Questrade MCP and writes them to the SQLite `investment_price` table. Trigger on `/questrade-refresh-prices` or "refresh questrade prices".
Allowed tools: Bash, Read, Write. Paths starting with `scripts/` are relative to this skill's folder.

## Constraints

- **Scope boundaries**: Only USD-denominated investments are updated; excludes synthetic cash rows (`CASH_USD`).
- **Batching limits**: Questrade `get_quotes` accepts a maximum of 20 symbols per request.
- **Independence**: Never implicitly sync holdings or change target weights during a price refresh.

## Quick start

Execute price refresh for held portfolio positions:

```bash
python3 scripts/questrade_price_refresh.py --help
```

Use `--full-watchlist` to include all watchlisted securities.

## Workflow

1. **Select Eligible Symbols**:
   - Default: Held positions where `account_investment.quantity > 0` and currency is USD.
   - `--full-watchlist`: All active watchlist securities.
2. **Batch MCP Queries**:
   Divide symbols into chunks of $\le 20$ and call MCP tool `Get Quotes(symbols=[...])`.
3. **Stage Payload**:
   Combine responses into `temp/questrade_price_refresh_payload.json`.
4. **Persist Prices**:
   ```bash
   python3 scripts/questrade_price_refresh.py --payload temp/questrade_price_refresh_payload.json
   ```
5. **Clean & Report**:
   Remove temporary JSON payload and display summary of updated prices in chat.

## Verification

- Confirm prices updated in SQLite `investment_price` table.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade Tool Schemas](../questrade-tool-schemas.md): Schema for `get_quotes` input and output.
