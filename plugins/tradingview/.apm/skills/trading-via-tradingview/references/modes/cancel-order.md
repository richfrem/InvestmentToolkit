# Mode: cancel-order (`/tv-cancel-order`)

Cancel a Working or Inactive order in TradingView via CDP and mark it cancelled in the Trade Log. Trigger on /tv-cancel-order or 'cancel order [ID]'.
Allowed tools: Bash, Read, Write.

Cancel a Working or Inactive order in TradingView via CDP and mark it cancelled in the Trade Log.


## Constraints

- Human confirmation: Never cancel live orders without explicit user confirmation of the order UUID and ticker.
- Trade log sync: Mark status as CANCELLED in `domain_model.sqlite` upon successful cancellation.
- Working orders only: Confirm order is in Working or Inactive status before dispatching click.

## Quick start

```bash
python3 investment_screener/backend/py_services/place_order.py --cancel <ORDER_UUID>
```

## Workflow

1. List open orders via [get-orders mode](get-orders.md) to locate target order UUID.
2. Display confirmation card with Ticker, Side, Shares, and Price to user.
3. On user confirmation, execute cancel via CDP: click cancel button on order row.
4. Record cancellation in `domain_model.sqlite` order table.

## Verification

- Confirm order no longer appears in Working orders table in broker panel.
- Validate routing cases against `evals/evals.json`.
