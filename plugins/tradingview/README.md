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
| **Portfolio Sync** | **`/tv-portfolio-sync`** | **Sync portfolio.json from live TV broker panel (TFSA + RRSP + Cash). Shows diff before writing. No Broker API needed.** |
| **Place Order** | **`/place-order buy\|sell N TICKER in ACCOUNT`** | **Live order execution via TradingView CDP automation. 3-step HITL: preflight → fill dialog + screenshot → CONFIRM. Records `tvOrderId` on trade log entry.** |
| **Cancel Order** | **`/cancel-order {tvOrderId}`** | **Cancel a Working/Inactive order by UUID — clicks × in TV broker panel, handles secondary confirmation dialog, marks trade log cancelled.** |
| **Modify Order** | **`/modify-order {tvOrderId} {newPrice}`** | **Modify limit price on a Working/Inactive order — clicks ✏, fills price via CDP keyboard events (React-safe), clicks Confirm/Send Order.** |
| **Get Orders** | **`/get-orders`** | **List open Working/Inactive orders from TradingView broker panel, including order UUIDs.** |
| Pine Inject | `/pine-inject {description}` | Generate a Pine Script v6 indicator from description and inject via CDP. Preflight validates `//@version=6` and `indicator()`. |
| Author Pine Script | `/author-pine-script {description}` | Full authoring workflow: source research → `pine_linter.py` lint gate → inject → save to TV library. |
| **Deep TA** | **`/tv-ta-deep {TICKER} [TIMEFRAME]`** | **Deep TA with custom indicator view construction, multi-timeframe context, synthesized entry/trim/exit levels, red-team review. `ta-guide` agent for interactive session.** |
| **Daily TA Sweep** | **`/ta-daily-sweep`** | **Batch TA scan of all portfolio holdings in one CDP session. Reads Data Window (RSI, ADX, Vol Bias, Squeeze, Volume) per ticker. Flags abnormal volume, momentum extremes, squeeze setups. Cross-references DCF projections. Outputs ranked report: REDUCE / MONITOR / ACCUMULATE / HOLD.** |

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

### CDP Chart Control Commands (direct CLI)

These low-level commands are used by skills to prepare the chart before analysis:

```bash
# Add/remove indicators
node tradingview-cdp/cli.js chart addIndicator "RSI"
node tradingview-cdp/cli.js chart addIndicator "AI TA Levels"   # personal library script
node tradingview-cdp/cli.js chart removeIndicator "RSI"
node tradingview-cdp/cli.js chart indicators     # list all on chart

# Timeframe and symbol
node tradingview-cdp/cli.js chart timeframe 1D   # daily
node tradingview-cdp/cli.js chart timeframe W    # weekly
node tradingview-cdp/cli.js chart timeframe 240  # 4-hour
node tradingview-cdp/cli.js chart symbol NVDA

# Data Window — read numeric indicator values
node tradingview-cdp/cli.js chart openDataWindow  # open panel + switch tab
node tradingview-cdp/cli.js chart read            # returns JSON of all indicator values

# Pine Script
node tradingview-cdp/cli.js pine inject --file plugins/tradingview/assets/pinescript-indicators/ai-ta-levels.pine
node tradingview-cdp/cli.js pine save "AI TA Levels"
node tradingview-cdp/cli.js pine read             # read current Pine Editor content
```

**Critical**: `addIndicator` uses `Input.dispatchMouseEvent` at the button's `getBoundingClientRect()` center — not `.click()`, which opens the timezone dropdown instead. Result selector: `div[class*="container-WeNdU0sq"]`. **Close the Pine Editor before calling `addIndicator`** — when the Pine Editor panel is open the Indicators dialog search input is not found.

**Source code viewing**: Open the Indicators dialog (Indicators toolbar button) → search for any indicator → view source for any open-source script from the result row. Also accessible via chart legend More menu → "Source code…" (unicode `…`). PA Toolkit Lite [UAlgo] IS open source (CC BY-NC-SA 4.0) and source is accessible this way.

---

### Custom Pine Script Indicators

Indicator files live at `plugins/tradingview/assets/pinescript-indicators/`:

| File | Purpose |
|------|---------|
| `ai-ta-levels.pine` | Multi-EMA (21/50/200) + volume bias % — designed to give AI precise numeric levels from the Data Window without relying on screenshot OCR |
| `community-reference/pa-toolkit-lite-ualgo.pine` | PA Toolkit Lite source (CC BY-NC-SA 4.0) — reference for `type` UDTs, `box.new()` order blocks, `ta.pivothigh`/`ta.pivotlow` liquidity detection patterns |

Lint before injecting: `python3 plugins/tradingview/skills/author-pine-script/scripts/pine_linter.py <file.pine>`

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

# Daily portfolio TA sweep — scans all holdings, writes TECHNICAL_SWEEP events to the Intelligence Ledger
python3 plugins/tradingview/scripts/ta_sweep_batch.py
python3 plugins/tradingview/scripts/ta_sweep_batch.py --skip HUMN,WYFI    # skip specific tickers
python3 plugins/tradingview/scripts/ta_sweep_batch.py --delay 1200         # faster scan (~1.2s/ticker)
python3 plugins/tradingview/scripts/ta_sweep_batch.py --save-results PATH  # also export a flat-file JSON snapshot (opt-in)
# Results written to the Intelligence Ledger (TECHNICAL_SWEEP events) / SQLite read-model, not to a flat JSON file by default.

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
├── cli.js           ← entry point — all commands registered here
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
    ├── trading.js   ← full order automation:
    │                   preflight, executeOrder, confirmAndSubmit,
    │                   cancelOrder, modifyOrder, submitModify,
    │                   verifyOrderInBrokerPanel, _findOrderRowAndAct
    ├── chart.js     ← chart control:
    │                   changeTimeframe, changeSymbol, changeChartType,
    │                   addIndicator, removeIndicator, listIndicators,
    │                   readDataWindow, openDataWindow, saveLayout
    └── pine.js      ← Pine Script editor:
                        injectPineScript, savePineToLibrary,
                        readIndicatorValues, removePineScript,
                        readSourceFromDialog
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
1. /update-stock-analysis CRWV        → fresh DCF
2. /tv-alert-sync CRWV         → set alerts at new bear/base/bull targets
```
