# TradingView Plugin

Real-time price integration for InvestmentToolkit via TradingView Desktop and Chrome DevTools Protocol (CDP).

---

## Requirements

### TradingView Desktop (required)

You must have **TradingView Desktop** installed on your machine.

- Download: https://www.tradingview.com/desktop/
- macOS install path: `/Applications/TradingView.app`
- The app must be launched with the `--remote-debugging-port=9222` flag for this plugin to connect. The startup script (`run_investment_toolkit.py`) handles this automatically.

### TradingView Premium subscription (required for real-time data)

This plugin reads price data directly from your TradingView session. **A Premium or higher subscription is required** to get real-time (non-delayed) quotes.

- Free accounts: data is delayed 15–20 minutes — same as yfinance, no improvement
- Essential / Plus / Premium+: real-time data — this is the improvement the plugin provides
- See plans: https://www.tradingview.com/pricing/

Without a Premium subscription the plugin still works (it reads from your active chart), but the prices won't be any fresher than the yfinance fallback.

### Node.js 18+ (required)

The owned CDP client (`tradingview-cdp/cli.js`) runs on Node.js.

```bash
node --version   # must be 18+
```

### One-time setup

```bash
cd tradingview-cdp
npm ci
cd ..

# Verify
python3 plugins/tradingview/scripts/tv_health_check.py
```

---

## How It Works

```
Python script
  └─ subprocess → tradingview-cdp/cli.js  (owned, no external MCP server)
        └─ Chrome DevTools Protocol (localhost:9222)
              └─ TradingView Desktop
                    └─ Your Premium real-time feed
```

TradingView Desktop is launched at startup with `--remote-debugging-port=9222`. The Python scripts connect to it via the owned Node.js CLI and read the active chart's price and change%.

**yfinance is not replaced** — it remains the source for:
- Historical OHLCV (1w, 1m, YTD, 1y price changes)
- Financial fundamentals (revenue, margins, EPS, ratios) used in DCF
- All data when TradingView Desktop is closed

TradingView adds a real-time price layer **only for current price and 1d change%**.

**Automatic fallback:** if TradingView is not running or not reachable, every script silently falls back to yfinance. The screener, heatmap, and portfolio table continue working exactly as before.

---

## Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| Price Refresh | `/tv-price-refresh` | Live prices for all portfolio positions (TV → yfinance fallback per ticker) |
| Alert Sync | `/tv-alert-sync` | Create TradingView price alerts at DCF bear/base/bull targets |
| Alert Sync (single) | `/tv-alert-sync CRWV` | Alert sync for one ticker |
| Chart Snapshot | `/tv-snapshot CRWV` | Capture chart screenshot → `PortfolioAnalysis/screenshots/` |
| TA Snapshot | `/tv-ta CRWV` | Screenshot + visual technical analysis — trend, S/R levels, indicator readings, buy/sell zones |
| **Portfolio Sync** | **`/tv-portfolio-sync`** | **Sync portfolio.json from live TV broker panel (TFSA + RRSP + Cash). Shows diff before writing. No Questrade API needed.** |
| **Place Order** | **`/place-order buy\|sell N TICKER in ACCOUNT`** | **Live order execution via TradingView CDP automation. 3-step HITL: preflight → fill dialog + screenshot → CONFIRM. Records `tvOrderId` on trade log entry.** |
| **Cancel Order** | **`/cancel-order {tvOrderId}`** | **Cancel a Working/Inactive order by UUID — clicks × in TV broker panel, handles secondary confirmation dialog, marks trade log cancelled.** |
| **Modify Order** | **`/modify-order {tvOrderId} {newPrice}`** | **Modify limit price on a Working/Inactive order — clicks ✏, fills price via CDP keyboard events (React-safe), clicks Confirm/Send Order.** |
| **Get Orders** | **`/get-orders`** | **List open Working/Inactive orders from TradingView broker panel, including order UUIDs.** |

### `/tv-ta` — Technical Analysis Snapshot

Captures a live chart screenshot and runs a full visual TA analysis using Claude's vision:

```
/tv-ta CRWV        # TA on current CRWV chart
/tv-ta NVDA 1W     # Weekly chart TA (note the timeframe for context)
```

**What you get:**
- Trend direction (higher highs/lows or range-bound)
- Key support and resistance levels read directly from the chart
- Indicator readings for whatever you have configured in TradingView (RSI, MACD, MAs, volume, Bollinger Bands, etc.)
- Buy zone with entry range, invalidation (stop) level, and risk/reward ratio
- Sell/trim zone at next logical resistance
- DCF cross-reference: if a projection exists for the ticker, the TA levels are mapped against bear/base/bull scenarios

**Setup tip:** Configure your TradingView chart with the indicators you want before running `/tv-ta`. The skill reads whatever is on screen — add RSI, MACD, volume, moving averages in TradingView Desktop first for richer analysis.

---

## Scripts (direct use)

All scripts run from the repo root:

```bash
# Single ticker quote (reads active chart; label shows requested symbol)
python3 plugins/tradingview/scripts/tv_quote.py CRWV

# Batch quotes
python3 plugins/tradingview/scripts/tv_batch_quotes.py '["CRWV","NVDA","INTC","AMD"]'

# Create DCF alerts for all holdings
python3 plugins/tradingview/scripts/tv_create_alerts.py

# Create DCF alerts for one ticker
python3 plugins/tradingview/scripts/tv_create_alerts.py --ticker CRWV

# Dry run (shows what would be created)
python3 plugins/tradingview/scripts/tv_create_alerts.py --dry-run

# Health check
python3 plugins/tradingview/scripts/tv_health_check.py
python3 plugins/tradingview/scripts/tv_health_check.py --json

# Launch TradingView manually (also done automatically at startup)
python3 plugins/tradingview/scripts/tv_launch.py

# --- Order Management (requires TradingView Desktop + broker connected) ---

# List open Working/Inactive orders with UUIDs
python3 plugins/tradingview/scripts/tv_get_orders.py
python3 plugins/tradingview/scripts/tv_get_orders.py --ticker INTC --json

# Modify a limit order price (finds row by UUID, fills form via keyboard events)
python3 plugins/tradingview/scripts/tv_modify_order.py \
    --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12 \
    --new-price 47.00 --ticker INTC --action buy

# Cancel an order (clicks × row button, handles secondary confirmation dialog)
python3 plugins/tradingview/scripts/tv_cancel_order.py \
    --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12 \
    --ticker INTC --action buy

# Place an order (full HITL flow — use place_order.py for preflight/execute/submit)
python3 investment_screener/backend/py_services/place_order.py \
    --ticker INTC --action buy --shares 1 --order-type limit --limit-price 45.00 \
    --account tfsa --preflight
```

---

## Port 9222 Conflict

Port 9222 is the standard Chrome DevTools remote debugging port. If Google Chrome or a browser-based tool is already using it, the health check will report port 9222 as "reachable" but CLI calls will fail or time out because the target is Chrome, not TradingView.

**Fix:** close any app that uses remote Chrome DevTools on port 9222 before launching TradingView, or ensure they don't start together.

---

## Node.js CDP Client

The plugin owns its Node.js CDP code at `tradingview-cdp/`. There is no runtime dependency on `tradingview-cdp` or any external MCP server.

```
tradingview-cdp/
├── cli.js           ← entry point (status, quote, alert, screenshot)
├── router.js        ← command dispatcher
├── connection.js    ← CDP connect / evaluate helpers
├── package.json     ← single dep: chrome-remote-interface
└── core/
    ├── data.js      ← getQuote, getOhlcv, getStudyValues
    ├── alerts.js    ← create, list, delete
    ├── health.js    ← healthCheck
    ├── capture.js   ← captureScreenshot → PortfolioAnalysis/screenshots/
    ├── audit.js     ← appendAuditEvent → audit/orders-YYYY-MM-DD.jsonl
    ├── broker_data.js ← readBrokerPositions, readBrokerAccounts (for /tv-portfolio-sync)
    └── trading.js   ← full order automation:
                         preflight, executeOrder, confirmAndSubmit,
                         cancelOrder, modifyOrder, submitModify,
                         verifyOrderInBrokerPanel, _findOrderRowAndAct
```

### Order Automation Key Implementation Notes

**`cancelOrder`** — uses search-first approach (no tab navigation). Tab navigation was toggling the broker panel closed. Finds the order row by UUID directly in the current DOM, clicks `buttonIndex: -1` (last button = ×). Handles secondary "Cancel order / Keep order" dialog.

**`modifyOrder`** — clicks `buttonIndex: -2` (pencil ✏). Uses CDP keyboard events (`Input.insertText`) to fill the price field — **not** React property setter. Setting `input.value` directly shows the value visually but doesn't fire `onChange`, so TV submits the original price. Keyboard events properly trigger React's event chain.

**`submitModify`** — looks for "Confirm" / "Send Order" / "Save" / "Modify" / "Apply" buttons. Also handles secondary TV confirmation dialogs. Calls `verifyOrderInBrokerPanel` afterwards to confirm the new price.

**`tvOrderId`** — extracted from `verifyOrderInBrokerPanel` after submission and stored on the trade-log entry. Used by cancel/modify to locate the exact order row.

---

## Recommended Workflow

**Daily:**
```
1. run_investment_toolkit.py   → launches screener + TradingView Desktop automatically
2. /tv-price-refresh           → check where all positions are right now
3. /x-news-sweep               → daily news sweep
```

**After a stock evaluation:**
```
1. /evaluate-stock CRWV        → fresh DCF
2. /tv-alert-sync CRWV         → set alerts at new bear/base/bull targets
```
