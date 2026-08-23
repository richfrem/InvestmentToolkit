---
name: tv-ta-snapshot
plugin: tradingview
description: >
  Captures a TradingView chart screenshot and performs visual technical analysis.
  Reads the live chart image (with whatever indicators the user has configured)
  and produces support/resistance levels, trend assessment, and buy/sell price zones.
  Optionally cross-references DCF fair value from projections/.
  Trigger on /tv-ta TICKER, "technical analysis TICKER", or "TA snapshot TICKER".
allowed-tools: Bash, Read
---

# TradingView Technical Analysis Snapshot Skill

## What This Skill Does

1. **Checks** TradingView Desktop is reachable (port 9222)
2. **Captures** a screenshot of the current chart for the requested ticker
3. **Reads** the image using Claude's vision capability
4. **Analyzes** the chart: trend, key levels, indicator readings, volume
5. **Outputs** structured buy/sell zone recommendations
6. **Cross-references** DCF fair value from `projections/` if available

---

## Phase 1 — Parse Argument

Extract the ticker from the trigger:
- `/tv-ta CRWV` → ticker = `CRWV`
- `"technical analysis NVDA"` → ticker = `NVDA`
- `"TA snapshot INTC"` → ticker = `INTC`

If no ticker provided, ask: `"Which ticker would you like to analyze?"`

Also accept optional timeframe hint: `/tv-ta CRWV 1D` → note the timeframe for context in the analysis. If not provided, assume daily.

---

## Phase 2 — Health Check

```bash
python3 "$(find plugins/tradingview/scripts ~/.claude/plugins/cache -name tv_health_check.py -path "*/tradingview/*" 2>/dev/null | sort | tail -1)" --json
```

If TradingView is **not** running:

```
TradingView Desktop not detected on port 9222.
TA snapshots require TradingView Desktop to be running with your chart open.

Launch it: python3 plugins/tradingview/scripts/tv_launch.py
Or:        open -a TradingView --args --remote-debugging-port=9222
```

Stop if TradingView is not available.

---

## Phase 3 — Load DCF Context (Optional, Best-Effort)

Check for a saved projection to use as fair value anchor:

```bash
ls investment_screener/backend/data/projections/ | grep -i "TICKER"
```

If found, read the most recent one:
```bash
# Read the projection file (most recent by filename date)
```

Extract:
- `aiThesis.fairValue` — weighted fair value
- `scenarios.bear.scenarioPrice` — bear case
- `scenarios.base.scenarioPrice` — base case
- `scenarios.bull.scenarioPrice` — bull case
- `aiThesis.action` — current thesis action (BUY / MAINTAIN / REDUCE / EXIT)

If not found, proceed without DCF context and note it in the output.

---

## Phase 4 — Capture Screenshot

```bash
DATE=$(python3 -c "from datetime import date; print(date.today().isoformat())")
SAVE_DIR="PortfolioAnalysis/screenshots/$DATE"
mkdir -p "$SAVE_DIR"

node tradingview-cdp/cli.js screenshot --output "$SAVE_DIR/${TICKER}_ta"
```

The saved path will be: `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}_ta.png`

**Important:** The screenshot captures whatever the user currently has on screen in TradingView Desktop, including all configured indicators (RSI, MACD, moving averages, volume, Bollinger Bands, etc.). Tell the user upfront: "Make sure TradingView is showing the chart and timeframe you want analyzed before proceeding."

---

## Phase 5 — Visual Technical Analysis

Read the screenshot file:

```
Read: PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}_ta.png
```

Then analyze the image rigorously. For each section, only report what is clearly visible in the chart — do not speculate about indicators that aren't shown.

### Analysis Framework

**1. Timeframe & Price Context**
- Current price (read from chart if visible)
- Timeframe (daily / weekly / intraday)
- Date range visible

**2. Trend Structure**
- Primary trend direction: Uptrend / Downtrend / Sideways
- Evidence: higher highs + higher lows, or lower highs + lower lows, or range-bound
- Recent price action: momentum accelerating, decelerating, or stalling

**3. Key Price Levels**
List each level with its type and significance:
- **Support levels** — prior swing lows, consolidation zones, moving average confluences
- **Resistance levels** — prior swing highs, unfilled gaps, round numbers
- **Trend lines** — if visible and clearly drawn on the chart

**4. Indicator Readings** (only for indicators visible in screenshot)
For each visible indicator:
- **Moving Averages**: position relative to price, any recent crossovers, slope direction
- **RSI**: current reading, overbought (>70) / oversold (<30) / neutral, divergences
- **MACD**: histogram direction, signal line crossover, bullish/bearish momentum
- **Volume**: above/below average, volume on up-days vs down-days, climactic spikes
- **Bollinger Bands**: price relative to bands, band width (volatility expansion/contraction)
- **Any other indicators visible** — describe what you see

**5. Candlestick / Pattern Observations**
- Any significant recent candle patterns (doji, hammer, engulfing, etc.)
- Chart patterns (cup & handle, head & shoulders, flag, wedge, etc.) if visible

**6. Risk/Reward Assessment**
Given the above, identify:
- **Best buy zone**: price range where risk/reward is most favorable (near support with clear invalidation level)
- **Invalidation level**: price below which the bullish thesis fails
- **Target zone**: price range of next logical resistance
- **Risk/reward ratio**: estimated (target distance ÷ stop distance)

---

## Phase 6 — DCF Integration (if projections found)

After the TA analysis, add a cross-reference section:

```
DCF CROSS-REFERENCE
───────────────────
Fair Value:  $XX.XX  (weighted: bear/base/bull)
Bear Case:   $XX.XX
Base Case:   $XX.XX
Bull Case:   $XX.XX
Thesis:      BUY / MAINTAIN / REDUCE / EXIT

TA vs DCF Alignment:
- [Current price] is [X%] below/above fair value of [$XX]
- Best buy zone [$low–$high] is [X%] below/above fair value
- If buy zone aligns with DCF margin of safety: CONFIRMED — strong R/R entry
- If buy zone is above fair value: NOTE — TA entry may not offer DCF margin of safety
```

---

## Phase 7 — Output

Format the final analysis as:

```
╔══════════════════════════════════════════════════════════════════╗
║         TECHNICAL ANALYSIS SNAPSHOT — {TICKER}                   ║
╚══════════════════════════════════════════════════════════════════╝

Captured:  {YYYY-MM-DD HH:MM}
Chart:     TradingView Desktop (live at time of capture)
Timeframe: {timeframe}
Price:     ${current price if readable}

TREND
  Direction:  Uptrend / Downtrend / Sideways
  Momentum:   Accelerating / Decelerating / Stalling

KEY LEVELS
  Resistance: $XX.XX — [description]
              $XX.XX — [description]
  Support:    $XX.XX — [description]
              $XX.XX — [description]

INDICATORS
  [Name]:  [Reading] — [Interpretation]
  ...

BUY ZONE
  Entry range:    $XX.XX – $XX.XX
  Invalidation:   $XX.XX (stop below)
  Target:         $XX.XX – $XX.XX
  Risk/Reward:    ~X.X:1

SELL / TRIM ZONE
  Trim range:     $XX.XX – $XX.XX
  Reason:         [resistance level / extended / overbought]

[DCF CROSS-REFERENCE — if projections available]

Screenshot saved: PortfolioAnalysis/screenshots/{date}/{TICKER}_ta.png
```

---

## Error Handling

| Situation | Response |
|-----------|----------|
| TradingView not running | Print launch instructions and stop |
| Screenshot capture fails | Report CLI error, do not attempt analysis |
| Image unreadable / blank | Tell user to check TradingView Desktop is showing the chart |
| No DCF projection found | Proceed without DCF section, note absence |
| Indicators unclear in image | Only analyze what is clearly visible; note what couldn't be read |

---

## Hard Rules

1. **Never fabricate levels** — only cite prices clearly visible in the chart image
2. **Never skip the health check** — TradingView must be confirmed running before screenshotting
3. **Flag indicator absence** — if RSI isn't on the chart, don't report RSI readings
4. **Always provide invalidation** — every buy zone recommendation must include a stop level
5. **DCF is context, not override** — TA analysis is independent; DCF is an add-on cross-check

---

## CDP Chart Control Reference

These commands are available via `node tradingview-cdp/cli.js` for pre-analysis chart setup:

### Indicator Management
```bash
# Add a built-in or saved personal indicator
node tradingview-cdp/cli.js chart addIndicator "RSI"
node tradingview-cdp/cli.js chart addIndicator "AI TA Levels"   # personal library script

# Remove an indicator by legend display name
node tradingview-cdp/cli.js chart removeIndicator "RSI"

# List all indicators currently on chart (reads Data Window)
node tradingview-cdp/cli.js chart indicators
```

**Critical**: `addIndicator` opens the Indicators dialog via `Input.dispatchMouseEvent` at the button's computed `getBoundingClientRect()` center — not `.click()`, which is unreliable on this button.

**Pine Editor blocking `addIndicator`**: When the Pine Editor dialog (`editorBaseLayoutContainer-dialog-z_CXxRZA`) is open, it blocks the Indicators search input. The `pine-dialog-button` `aria-pressed` attribute does NOT reliably reflect dialog visibility — check DOM presence instead. **Preferred fix**: after `pine inject` + `pine save`, click the "Update on chart" / "Add to chart" button directly (match by title: `/(?:add|update).*(?:to|on).*chart/i`). This works without closing the editor:
```javascript
// Via CDP evaluate:
const btn = [...document.querySelectorAll('button')].find(b =>
  /(?:add|update).*(?:to|on).*chart/i.test(b.title));
// Then Input.dispatchMouseEvent at btn.getBoundingClientRect() center
```

Result row selector: `div[class*="container-WeNdU0sq"]` — all result rows (built-in and community) share `platform-WeNdU0sq` which is NOT useful for filtering. Match priority: (a) exact text match, (b) first result (TV's top-ranked), (c) contains match.

### Timeframe & Symbol
```bash
node tradingview-cdp/cli.js chart timeframe 1D    # daily
node tradingview-cdp/cli.js chart timeframe W     # weekly
node tradingview-cdp/cli.js chart timeframe 240   # 4-hour
node tradingview-cdp/cli.js chart symbol NVDA
```

### Data Window Read
```bash
node tradingview-cdp/cli.js chart openDataWindow   # open panel + switch to Data Window tab
node tradingview-cdp/cli.js chart read             # read all visible indicator values as JSON
```
Data Window provides numeric EMA, RSI, volume readings for precise analysis without screenshot guessing. The stable selector is `[data-test-id-value-title]`.

### Pine Script (Custom Indicators)
```bash
# Inject and add to chart (also saves to TV library on first use)
node tradingview-cdp/cli.js pine inject --file plugins/tradingview/assets/pinescript-indicators/ai-ta-levels.pine

# Save current Pine Editor script to TV personal library
node tradingview-cdp/cli.js pine save "AI TA Levels"

# Add saved personal script to chart via Indicators dialog
node tradingview-cdp/cli.js chart addIndicator "AI TA Levels"
```

### Viewing Indicator Source
Two paths to view open-source indicator source:
1. **Chart legend More menu**: hover legend row → `button[aria-label="More"]` → `"Source code…"` (unicode `…` not `...`). Only appears for open-source community scripts.
2. **Indicators dialog full list**: open via Indicators toolbar button → search → source icon on result row. Accessible for any open-source script (including PA Toolkit Lite [UAlgo] — CC BY-NC-SA 4.0).

Closed-source scripts (e.g., paid/private) do not show either option.

---

## Custom Indicator: AI TA Levels

**File**: `plugins/tradingview/assets/pinescript-indicators/ai-ta-levels.pine`

A custom overlay indicator built for AI-assisted TA snapshots. Plots:
- **EMA stack** (21/50/200) — precise numeric levels readable from Data Window
- **Volume bias %** — bull vs bear volume MA ratio, shown in Data Window and as a last-bar label
- **Trend state label** — `BULL X%` / `BEAR X%` / `NEUT X%` on the last bar

Use before `/tv-ta` snapshots when the chart doesn't have EMA levels visible, so Data Window read gives precise support/resistance numbers without relying on screenshot OCR.

---

## Community Reference Indicators

Saved to `plugins/tradingview/assets/pinescript-indicators/community-reference/`:

| File | What to borrow |
|------|---------------|
| `pa-toolkit-lite-ualgo.pine` | `type` UDT pattern, `box.new()` order blocks with `xloc.bar_time`, `ta.pivothigh`/`ta.pivotlow` for liquidity levels, `ta.change(trend)` ZigZag pattern, max-size array shift |
