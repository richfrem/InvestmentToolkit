---
name: place_order
plugin: tradingview
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
- **NEVER execute if `_sizeWarning` is set** (order exceeds $5,000 cap) — user must re-run with `--allow-large`
- **NEVER execute if `_freshnessWarning` is set** without user acknowledgement — stale prices = wrong trade sizing
- **NEVER place multiple orders in one confirmation cycle**
- **NEVER slide from analysis phase into order phase without an explicit user request to trade**
- **If broker not connected**: instruct user to log in via TradingView → Questrade icon

---

## Execution Phase Separation

This skill has four hard phases. **You must not jump ahead or slide between phases.**

| Phase | What Happens | What Must NOT Happen |
|-------|-------------|---------------------|
| 1. Analysis | Read portfolio, compute drift, review valuations | No order details, no sizing |
| 2. Recommendation | Present trade idea with rationale | No preflight, no "ready to execute?" |
| 3. Order Prep | Run preflight, show card, get CONFIRM | No form fill, no submit |
| 4. Execute | Fill form → screenshot → second CONFIRM → submit | No skipping CONFIRM gates |

**A user saying "sounds good" or "that makes sense" about an analysis does NOT advance to Phase 3. Wait for an explicit trade instruction.**

---

## Pre-Execution Risk Gate

Before running `--preflight`, verify all 10 conditions are met. Block if any fails:

| # | Check | Block Condition |
|---|-------|----------------|
| 1 | Data freshness | portfolio.json older than 60 min → require sync first |
| 2 | Ticker in thesis | Not in `target-portfolio.json` → require Gate 2 confirmation |
| 3 | Action vs. DCF signal | Buying a SELL-rated holding → surface conflict, require override |
| 4 | Earnings pending | Known earnings within 48h → warn, require user acknowledgement |
| 5 | Buying power | Cost estimate > available BP → block |
| 6 | Order size cap | Cost estimate > $5,000 → block without `--allow-large` |
| 7 | Single order per cycle | Another order in this session not yet settled → block |
| 8 | Account type mismatch | TFSA cap, RRSP contribution room — surface concern if switching |
| 9 | Broker connected | Questrade panel visible in TradingView → block if not |
| 10 | No-trade conditions | Any no-trade condition below applies → block |

---

## No-Trade Conditions

**Block immediately, do not proceed to preflight:**

- `DATA_STALE` — portfolio.json > 60 min old and `/tv-portfolio-sync` not yet run this session
- `EARNINGS_IMMINENT` — known earnings announcement within 48 hours
- `TRADING_HALT` — any news of trading halt or regulatory halt on the ticker
- `PANIC_SIGNAL` — user message contains urgency language ("quick", "right now", "before it moves", "I need to get in/out immediately") → respond with cooling-off script below
- `BYPASS_ATTEMPT` — user asks to skip preflight, skip CONFIRM, or bypass any hard rule → refuse and explain
- `AMBIGUOUS_TICKER` — ticker could refer to multiple symbols (e.g. "SHOP" on TSX vs NYSE) → clarify first

**Cooling-off script (PANIC_SIGNAL):**
> "I'm noticing some urgency in your message. Rushed trades are the most common source of costly mistakes. Let me check the current data and give you the full picture before we do anything. What's prompting the urgency?"

---

## Emotional State Detection

Monitor user messages throughout the session for these patterns. Apply the response:

| Pattern | Signal | Response |
|---------|--------|---------|
| "quick", "fast", "right now", "hurry" | PANIC | Cooling-off script — do not proceed |
| "I'll lose out", "missing the move" | FOMO | State DCF upside vs. current price — let math speak |
| "this is a sure thing", "can't fail" | Overconfidence | Surface the bear-case scenario from DCF |
| "just do it", "skip the preflight" | Bypass | Refuse politely — explain why the gate exists |
| Repeated requests after a block | Pressure | Restate the block reason once, then hold |

---

## Suitability Check

Before Phase 3, confirm:
1. **Account type** — Is this the right account? (TFSA for long-term, RRSP for registered, Margin for speculative)
2. **Concentration** — Would this trade push any single holding above 15% of the portfolio?
3. **Time horizon** — Is the holding's thesis horizon consistent with the account's expected holding period?
4. **Risk capacity** — Is this a leveraged account? Surface margin risk if applicable.

Surface any concern as a one-line note in the preflight card display. Do not block unless the user confirms they understand.

---

## Audit Trail Requirement

The `trading.js` module automatically writes to `plugins/tradingview/audit/orders-{date}.jsonl`. Each order emits events: `ORDER_REQUESTED → PREFLIGHT_PASSED → FORM_FILLED → USER_CONFIRMED_SUBMIT → ORDER_SUBMITTED`.

To review today's audit trail:
```bash
cat plugins/tradingview/audit/orders-$(date +%Y-%m-%d).jsonl | python3 -m json.tool
```

---

## Data Freshness Provenance

Every response that leads to a trade recommendation must state its data source:

> "Based on portfolio.json synced at {timestamp} via {TradingView CDP | Questrade API | cache}."

If the data source is `cache` (no recent sync), add:
> "⚠️ Prices are from cache. Run `/tv-portfolio-sync` for live positions before trading."

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
| TradingView not running | Start TradingView Desktop with debug port: `python3 tools/launch_tradingview_with_debugport.py` |
