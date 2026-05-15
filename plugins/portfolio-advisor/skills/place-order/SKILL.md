---
name: place_order
plugin: portfolio-advisor
description: >
  Place a buy or sell order via TradingView's built-in Questrade broker
  integration using CDP DOM automation. Checks broker login, buying power,
  and account before showing a confirmation card. Fills the TradingView order
  dialog, screenshots the filled form for HITL review, then submits on explicit
  CONFIRM. Triggers a portfolio sync after execution. Trigger on /place-order,
  "buy X shares of TICKER", "sell N shares in ACCOUNT", or any trade execution request.
allowed-tools: Bash, Read, Write
---

# Place Order Skill — TradingView Broker Integration

## Quick Reference
- **Trigger**: `/place-order` or natural language ("buy 5 NVDA in TFSA", "sell 10 WYFI")
- **Execution path**: Python `place_order.py` → Node.js `trading.js` → CDP → TradingView order dialog
- **HITL Gate**: 3-step — preflight card → form-fill + screenshot → CONFIRM to submit
- **Post-execution**: Auto-syncs portfolio.json via QuestradeDataEngine

---

## ⚠️ Hard Rules

- **NEVER call `--submit` without explicit "CONFIRM" from the user**
- **NEVER skip the preflight step** — it checks broker login and buying power
- **NEVER execute if `_warning` is set** (insufficient buying power) 
- **NEVER place multiple orders in one confirmation cycle**
- **If broker not connected**: instruct user to log in via TradingView → Questrade icon

---

## Prerequisites — Broker Login Check

Before any order, verify TradingView has Questrade connected. The preflight will fail with a clear error if not. If broker is not connected, tell the user:

> "TradingView isn't showing an active Questrade connection. Open TradingView Desktop, click the broker icon (bottom-left area), and log in with your Questrade credentials. Once the account panel shows your positions, run the command again."

---

## Step 1: Gather Parameters

Extract from user message or ask:

| Parameter | Required | Notes |
|-----------|----------|-------|
| `--ticker` | ✓ | e.g. `WYFI`, `NVDA`, `SHOP.TO` |
| `--action` | ✓ | `buy` or `sell` |
| `--shares` | ✓ | Integer |
| `--order-type` | ✓ | `market`, `limit`, `stop`, `stop_limit` |
| `--limit-price` | If limit | Required for limit/stop_limit |
| `--account` | ✓ | `rrsp`, `tfsa`, `margin` |

---

## Step 2: Preflight — Check Broker Status + Buying Power

```bash
python3 investment_screener/backend/py_services/place_order.py \
  --ticker {TICKER} \
  --action {buy|sell} \
  --shares {N} \
  --order-type {market|limit|stop|stop_limit} \
  [--limit-price {PRICE}] \
  --account {rrsp|tfsa|margin} \
  --preflight
```

Output: ASCII confirmation card + JSON. Check:
- `connected: true` — Questrade is active in TradingView
- `_warning: null` — buying power is sufficient
- Correct `accountType` and `accountId`

If `_warning` is non-null → block. Tell user why. Do not proceed.

---

## Step 3: Present Card and Ask for CONFIRM

Show the user the full card. Then:

> "Does this look correct? Type **CONFIRM** to fill the TradingView order form, or tell me what to change."

Wait for exact **CONFIRM** (case-insensitive). Do not proceed on "yes", "ok", "sure".

---

## Step 4: Execute — Fill the TradingView Order Dialog

```bash
python3 investment_screener/backend/py_services/place_order.py \
  --ticker {TICKER} \
  --action {buy|sell} \
  --shares {N} \
  --order-type {market|limit|stop|stop_limit} \
  [--limit-price {PRICE}] \
  --account {rrsp|tfsa|margin} \
  --execute
```

This will:
1. Navigate the TradingView chart to the ticker
2. Click the Buy/Sell overlay button to open the order dialog
3. Fill in shares, order type, and limit price
4. Take a screenshot of the filled form
5. Return the screenshot path and the submit button text (e.g. "Buy 1 WYFI MARKET")

Show the user the `submitButtonText` and the screenshot path. Then ask:

> "The order form shows: **{submitButtonText}**. Screenshot saved at {screenshot_path}. Type **CONFIRM** to submit the order."

---

## Step 5: Submit — Only After Second CONFIRM

```bash
python3 investment_screener/backend/py_services/place_order.py --submit
```

This clicks the submit button in TradingView and then syncs portfolio.json.
Report the result to the user.

---

## Example Flows

### Market buy
```
User: /place-order buy 1 WYFI in TFSA
```
1. Preflight → show card with buying power
2. CONFIRM → `--execute` → form filled, screenshot taken
3. Show screenshot info + submit button text
4. CONFIRM → `--submit` → order placed + sync

### Limit buy
```
User: buy 5 NVDA at $140 limit in my TFSA
```
1. Preflight → cost estimate $700 USD vs USD buying power
2. CONFIRM → `--execute` with `--limit-price 140.00`
3. CONFIRM → `--submit`

### Sell
```
User: sell 10 WYFI market from TFSA
```
- Buying power check is skipped for sells (returning cash)
- Same 3-step flow applies

---

## Troubleshooting

| Error | Action |
|-------|--------|
| `No broker connected` | User must log in via TradingView → Questrade icon |
| `Order dialog did not open` | Tell user to ensure the chart is on the right ticker and the Questrade panel is visible in TradingView |
| `Shares input not found` | Dialog may have closed — re-run `--execute` |
| `Tab not found: Limit` | Order type not available for this symbol — try Market |
| TradingView not running | Start TradingView Desktop with debug port: `python3 launch_tradingview_with_debugport.py` |
