# Daily Portfolio TA Sweep Skill

## Trigger
`/ta-daily-sweep` or `/portfolio-scan`

## What This Skill Does

Batch technical analysis scan of all current portfolio holdings via TradingView CDP.
For each holding, reads the Data Window (RSI, Vol Bias, ADX, Squeeze, Volume) in one
CDP session — no screenshots, all numeric. Cross-references DCF projections and
target-portfolio.json for thesis context. Outputs a ranked daily report with
actionable flags: abnormal volume, momentum extremes, squeeze setups, distribution
patterns, and DCF fair value proximity.

**Complements `/x-news-sweep`** (fundamental/news lens) with a pure technical lens.
Run both at the start of a session for a full picture.

---

## Phase 0 — Health Check

```bash
python3 "$(find plugins/tradingview/scripts ~/.claude/plugins/cache -name tv_health_check.py -path "*/tradingview/*" 2>/dev/null | sort | tail -1)" --json
```

If TradingView is NOT connected:
```
TradingView Desktop not detected. The TA sweep requires TradingView running on port 9222.
Launch: python3 launch_tradingview_with_debugport.py
```
Stop if unhealthy.

---

## Phase 1 — Verify Data Files

Confirm both data files exist before running:
- `investment_screener/backend/data/portfolio.json` — current holdings
- `investment_screener/backend/data/theses/target-portfolio.json` — thesis/targets

If portfolio.json is stale (last_updated > 24h), suggest running `/tv-portfolio-sync` first.

---

## Phase 2 — Run Batch Sweep

```bash
python3 plugins/tradingview/scripts/ta_sweep_batch.py 2>&1
```

This will:
1. Read all holdings from `portfolio.json` (skips PSU.U.TO, USD_CASH)
2. Switch TradingView chart to each ticker sequentially
3. Read Data Window values via CDP (RSI, ADX, Vol Bias, Squeeze, Volume, ATR)
4. Compute technical flags per ticker
5. Cross-reference DCF projections for NEAR_FV / ABOVE_FV / DEEP_VALUE flags
6. Output enriched JSON to stdout

**Expected runtime:** ~4s per ticker. For 29 equity holdings: ~2 minutes.
Show the user: `"Scanning 29 holdings... (~2 minutes)"` before running.

The script reports progress to stderr: `[1/29] APLD`, `[2/29] BE`, etc.

---

## Phase 3 — Parse and Prioritize Results

The JSON output is an array of objects:

```json
{
  "ticker": "COIN",
  "close": 285.40,
  "changePct": 3.8,
  "rsi": 73.2,
  "rsima": 68.1,
  "volBias": -62.4,
  "adx": 28.3,
  "squeezeOn": false,
  "vol": 18400000,
  "volMA": 9200000,
  "volumeRatio": 2.0,
  "flags": ["RSI_OB", "DIST_SIGNAL", "VOLUME_SPIKE"],
  "action": "REDUCE",
  "targetAction": "ACCUMULATE",
  "targetWeight": 4.5,
  "dcf": { "fairValue": 312.00, "pctToFV": 9.3, "action": "BUY" }
}
```

**Sort by**: flag count descending (most flagged = most urgent to review).
**Action priority**: REDUCE > MONITOR > ACCUMULATE > HOLD.

---

## Phase 4 — Generate Report

Output a structured two-section report:

### Section 1: Action Items (flagged holdings only)

For each holding with flags, write a short analysis line (1-2 sentences) explaining:
- What the flag means in this specific context
- Why it matters for this holding (reference thesis action if available)
- Suggested next step

Format each as:
```
🔴 REDUCE   COIN   RSI 73.2 (OB) + Vol Bias -62% (DIST) + 2× volume spike
             Consider trimming — distribution into strength. DCF fair value $312 (9% away).
             Thesis says ACCUMULATE but technical setup is working against you short-term.

🟡 MONITOR  SNDK   DIST_SIGNAL + VOLUME_DRY on +5.3% day
             Big up day on below-average volume suggests weak conviction breakout.
             Wait for RSI > 70 + above-avg volume before adding. GTC entry $1,350.

🟢 ACCUM    APLD   RSI 28.1 (oversold) + DEEP_VALUE (40% below fair value)
             Technical oversold at fundamental value zone — high-conviction accumulate.
             Confirm: is this a sector sell-off or thesis-specific risk?
```

Emoji guide:
- 🔴 REDUCE / EXIT
- 🟡 MONITOR (watch but don't act yet)
- 🟢 ACCUMULATE
- ⚪ HOLD (no flags or clean setup)

### Section 2: Full Scan Summary Table

```
TICKER  PRICE    DAY%    RSI    ADX   VBIAS    V/MA   SQZ  ACTION
──────────────────────────────────────────────────────────────────
APLD    40.95   +2.1%   62.3   28.4   +12%    1.3×    —   HOLD
BE      14.20   -1.2%   41.2   18.3   -22%    0.9×    —   HOLD
...
```

Columns:
- PRICE: current close
- DAY%: daily change %
- RSI: RSI value (bold if >72 or <30)
- ADX: trend strength (note if >30 or <20)
- VBIAS: Vol Bias % (positive = bullish distribution, negative = bearish)
- V/MA: volume as multiple of volume MA
- SQZ: ✓ if squeeze on, — if off
- ACTION: derived action

### Section 3: Session Summary

```
SWEEP SUMMARY — {DATE} — {N} holdings scanned
  Action breakdown:   {X} REDUCE  |  {Y} MONITOR  |  {Z} ACCUMULATE  |  {W} HOLD
  Top flags:          DIST_SIGNAL (N), RSI_OB (N), VOLUME_SPIKE (N)
  Time to scan:       ~{T} seconds
  Data Window source: AI-TA (RSI, Vol Bias, ADX, Squeeze) + TV OHLCV
```

---

## Flag Reference

| Flag | Condition | Implication |
|------|-----------|-------------|
| `RSI_OB` | RSI > 72 | Overbought — watch for fade or fade confirmation |
| `RSI_OS` | RSI < 30 | Oversold — potential entry if thesis intact |
| `RSI_COOLING` | RSI < RSI-MA and RSI-MA > 62 | Momentum fading after hot run |
| `ADX_STRONG` | ADX > 30 | Trend confirmed — let it ride, tight stop |
| `ADX_WEAK` | ADX < 20 | Ranging — mean-reversion likely, fade breakouts |
| `SQUEEZE_ON` | Squeeze = 1 | Compression — big directional move coming |
| `DIST_SIGNAL` | Vol Bias < -50% | Down-volume dominating — distribution |
| `ACCUM_SIGNAL` | Vol Bias > +50% | Up-volume dominating — accumulation |
| `VOLUME_SPIKE` | Vol > 1.8× MA | Institutional activity — direction matters |
| `VOLUME_DRY` | Vol < 0.5× MA AND move > 2% | Weak-hand move — don't chase |
| `BIG_DAY` | \|daily%\| > 4% | Outsized move — confirm direction with volume |
| `NEAR_FV` | Price within 5% of DCF fair value | Approaching trim zone |
| `ABOVE_FV` | Price > DCF fair value | Above intrinsic — reduce |
| `DEEP_VALUE` | Price > 25% below DCF fair value | High-conviction accumulate zone |

---

## Action Logic

| Flags present | Derived Action |
|---------------|----------------|
| `RSI_OS` | ACCUMULATE |
| `ACCUM_SIGNAL` + `DEEP_VALUE` | ACCUMULATE |
| `ABOVE_FV` | REDUCE |
| `RSI_OB` + (`NEAR_FV` or `DIST_SIGNAL`) | REDUCE |
| `DIST_SIGNAL` + `VOLUME_DRY` | MONITOR |
| `VOLUME_SPIKE` or `BIG_DAY` | MONITOR |
| `SQUEEZE_ON` | MONITOR |
| Default | HOLD |

**Important**: `targetAction` from thesis may conflict with the derived TA action.
When they conflict, note the conflict explicitly — e.g., "Thesis says BUY but TA
says REDUCE — wait for RSI to cool before adding."

---

## Hard Rules

1. **Never suggest selling below DCF fair value** purely on TA signals alone —
   context the TA action against the fundamental target weight and action.
2. **VOLUME_SPIKE without direction context is not a sell signal** — it can mean
   accumulation or distribution. Check Vol Bias to determine direction.
3. **SQUEEZE_ON is a setup, not a signal** — don't act until the squeeze fires
   (price breaks out of the compression range).
4. **Conflicts between TA and thesis always get flagged** — the user decides.
5. **Do not modify any data files** during this skill — read-only.

---

## Script Reference

| Script | Purpose |
|--------|---------|
| `plugins/tradingview/scripts/ta_sweep_batch.py` | Python orchestrator — reads portfolio, calls CDP sweep, enriches with DCF |
| `tradingview-cdp/core/sweep.js` | Node.js CDP scan engine — symbol switching + Data Window reads |
| `tradingview-cdp/cli.js sweep --tickers A,B,C` | Direct CLI access to sweep engine |
