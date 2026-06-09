# 📊 Top TradingView Indicators: AI Agent Reference Guide

**Purpose:** This document serves as an extended knowledge base for AI agents developing Pine Script v6 strategies. It covers the most popular built-in and community-developed indicators on TradingView, providing their core mechanics, use cases, and Pine Script implementation insights from live source-code review.

> **Source review tool:** `python3 plugins/tradingview/skills/author-pine-script/scripts/pine_source_reader.py --name "<indicator name>"`
> Saves source to `temp/indicator_sources/<Name>.pine` for detailed inspection.

---

## 🏆 Verified TV Popularity Ranking (as of 2026-06, live from TV Top list)

| Rank | Indicator | Boosts | Pine | Key Pattern |
|------|-----------|--------|------|-------------|
| 1 | Smart Money Concepts [LuxAlgo] | 143.8K | v5 | Box/line arrays, `var` for OBs, `ta.pivothigh/low` |
| 2 | Squeeze Momentum [LazyBear] | 112.7K | v1 | BB inside KC = squeeze; `nz()` for momentum history |
| 3 | MacD Custom Indicator [ChrisMoody] | 79.5K | v1 | Color-coded histogram; `study()` (legacy) |
| 4 | SuperTrend [KivancOzbilgic] | 75.7K | v4 | ATR-based trailing stop; `ta.atr()` pattern |
| 5 | CM Williams Vix Fix [ChrisMoody] | 63.6K | v1 | WVF = highest(close,22)-low / highest(close,22) |
| 6 | WaveTrend Oscillator [LazyBear] | 58.9K | v1 | EMA of HLCC/3, smoothed CI oscillator |
| 7 | S&R Levels with Breaks [LuxAlgo] | 57.1K | v5 | `var` line arrays; pivot-based S/R |
| 8 | Market Structure Break & OB [EmreKb] | 54.3K | v5 | BOS/CHoCH detection via swing highs/lows |
| 9 | UT Bot Alerts [QuantNomad] | 50.8K | v4 | ATR trailing stop with cross signals |
| **10** | **ICT Killzones & Pivots [TFO]** | **48.2K** | **v6** | **Session time boxes (Asia/London/NY), pivot H/L per session, `input.session()`, timezone-aware** |
| 11 | Trendlines with Breaks [LuxAlgo] | 47.8K | v5 | Auto trendline detection + break alerts |
| 12 | Bollinger + RSI Double Strategy [ChartArt] | 45.9K | v1 | Combo strategy — BB squeeze + RSI filter |
| 13 | ADX and DI [BeikabuOyaji] | 44.5K | v4 | DMI with directional index coloring |
| ~15 | Nadaraya-Watson Envelope [LuxAlgo] | ~43K | v5 | Rational quadratic kernel; repaints on repaint=true |

---

## 🏆 Top Community Legends — Detailed Reference

### 1. Smart Money Concepts [LuxAlgo] — RANK #1
* **Pine version:** v5 (50,000+ lines; protected source in production; open-source version available)
* **Core mechanics:** Draws Order Blocks (OBs), Fair Value Gaps (FVGs), Change of Character (CHoCH), Break of Structure (BOS)
* **Key patterns from source:**
  - `var` used throughout for all `box`, `line`, and `label` arrays (correct draw-object pattern)
  - Uses `ta.pivothigh()` / `ta.pivotlow()` with configurable length for swing detection
  - `array.push()` / `array.shift()` for fixed-size FIFO arrays of OBs
  - Mitigation check: `high >= ob_top and low <= ob_bottom` within the OB validity window
* **v6 migration notes:** Replace `study()` → `indicator()`; `atr(n)` → `ta.atr(n)`; `highest(src,n)` → `ta.highest(src,n)`
* **Summary:** Ultimate institutional price-action toolkit. Study its OB array pattern — it's the gold standard.

### 2. Squeeze Momentum Indicator [LazyBear] — RANK #2
* **Pine version:** v1 (original 2014 script, still on v1 syntax)
* **Core mechanics:** Compares Bollinger Bands width to Keltner Channel width. BB inside KC = squeeze (red dot). Histogram direction predicts breakout direction.
* **Key patterns from source:**
  ```pine
  // BB vs KC squeeze detection
  sqzOn  = (lowerBB > lowerKC) and (upperBB < upperKC)
  sqzOff = (lowerBB < lowerKC) and (upperBB > upperKC)
  noSqz  = (sqzOn == false) and (sqzOff == false)
  // Momentum via linear regression delta
  val = linreg(source - avg(avg(highest(high,lengthKC), lowest(low,lengthKC)),sma(close,lengthKC)), lengthKC, 0)
  ```
* **v6 migration notes:**
  - `linreg(src,n,0)` → `ta.linreg(src,n,0)`
  - `sma(close,n)` → `ta.sma(close,n)`
  - `highest(high,n)` → `ta.highest(high,n)`
  - `lowest(low,n)` → `ta.lowest(low,n)`
  - `study()` → `indicator()`
  - `nz(val[1])` pattern — safe to keep; `nz()` works the same in v6
* **Summary:** Momentum + squeeze detection in ~40 lines. The `linreg` momentum calculation is reusable.

### 3. MacD Custom Indicator [ChrisMoody] — RANK #3
* **Pine version:** v1 (legacy `study()` syntax)
* **Core mechanics:** Standard MACD (12/26/9) with color-coded histogram bars showing if momentum is accelerating or decelerating
* **Key pattern:** Two-color histogram: green when histogram > prev bar, blue when falling (and vice versa for bearish)
* **v6 migration:** `study()` → `indicator()`; `macd()` → `ta.macd()`; color assignments same

### 4. SuperTrend [KivancOzbilgic] — RANK #4
* **Pine version:** v4
* **Core mechanics:** ATR multiplier creates upper/lower bands; trend direction flips when price crosses the band
* **Key pattern from source:**
  ```pine
  atr = ta.atr(atrPeriod)
  upperBand = hl2 + (factor * atr)
  lowerBand = hl2 - (factor * atr)
  // Persist previous band values
  upperBand := upperBand < nz(upperBand[1], upperBand) or close[1] > nz(upperBand[1], upperBand) ? upperBand : nz(upperBand[1], upperBand)
  lowerBand := lowerBand > nz(lowerBand[1], lowerBand) or close[1] < nz(lowerBand[1], lowerBand) ? lowerBand : nz(lowerBand[1], lowerBand)
  ```
* **v6 migration:** Already mostly v5-compatible; rename `study()` → `indicator()`; `nz()` pattern unchanged

### 6. WaveTrend Oscillator [LazyBear] — RANK #6
* **Pine version:** v1
* **Core mechanics:** Smoothed oscillator from HLCC/4 source
  ```pine
  ap  = hlc3
  esa = ema(ap, n1)
  d   = ema(abs(ap - esa), n1)
  ci  = (ap - esa) / (0.015 * d)
  tci = ema(ci, n2)
  wt1 = tci
  wt2 = sma(wt1, 4)
  ```
* **v6 migration:** `ema(src,n)` → `ta.ema(src,n)`; `sma(src,n)` → `ta.sma(src,n)`; `abs()` → `math.abs()`

### 10. ICT Killzones & Pivots [TFO] — RANK #10 (as of 2026-06)
* **Pine version:** v6 (native — no migration needed)
* **License:** Mozilla Public License 2.0
* **Core mechanics:** Draws colored session boxes (killzones) for institutional trading windows; detects pivot H/L within each session; boxes extend right until session closes
* **Key patterns from source review (723 lines):**
  ```pine
  // Session time window input — returns true when in session
  london_session  = input.session("0200-0500", "London Kill Zone",    defval=true)
  nyam_session    = input.session("0930-1100", "NY AM Kill Zone",     defval=true)
  nylunch_session = input.session("1200-1300", "NY Lunch Kill Zone",  defval=false)
  nypm_session    = input.session("1330-1600", "NY PM Kill Zone",     defval=true)
  asia_session    = input.session("2000-0000", "Asia Kill Zone",      defval=true)

  // Check if current bar is in a session
  in_london = na(time(timeframe.period, london_session, "America/New_York")) == false

  // Timeframe guard — only draw on lower timeframes
  valid_tf = timeframe.in_seconds('') <= timeframe.in_seconds('60')
  ```
* **Pivot detection within session:**
  ```pine
  // ta.pivothigh/low for session-scoped H/L
  ph = ta.pivothigh(high, pivot_len, pivot_len)
  pl = ta.pivotlow(low, pivot_len, pivot_len)
  // Extend box right until session end
  box.set_right(session_box, bar_index + 1)
  ```
* **Session time windows (EST / America/New_York):**
  - Asia: `2000-0000` (8 PM – midnight)
  - London: `0200-0500` (2 AM – 5 AM)
  - NY AM: `0930-1100` (the primary ICT window)
  - NY Lunch: `1200-1300` (low liquidity — often skip)
  - NY PM: `1330-1600` (afternoon reversal window)
* **Key insight:** `input.session()` returns a time-range string; wrap in `time(tf, session, timezone)` and check `!= na` to get a boolean. `timeframe.in_seconds('')` (empty string = current chart TF) lets you hide elements on higher timeframes.

### 9. UT Bot Alerts [QuantNomad] — RANK #9
* **Core mechanics:** ATR trailing stop that generates crossover buy/sell signals. Same engine as SuperTrend but with signal arrows rather than band fill.
* **Pattern:** `hsp = nz(hsp[1], src)` + conditional update based on close direction — same nz() persistence pattern as KivancOzbilgic SuperTrend.

### Nadaraya-Watson Envelope [LuxAlgo] — formerly #10, now ~#15
* **Pine version:** v5
* **Key insight:** Uses rational quadratic kernel for non-parametric regression. The envelope **repaints by design** on the non-repainting=false setting. If using as a signal, always set `repainting=false` and use `[1]` offsets.

---

## 📈 Trending Indicators (as of 2026-06)

Top trending scripts reflect current themes in the TV community:

| Indicator | Author | Theme |
|-----------|--------|-------|
| Smart Flow Momentum | GainzAlgo | Liquidity footprint + trend |
| Liquidity Sweeps & BOS | AlgoAlpha | ICT liquidity concepts |
| Smart Volume Profile | BigBeluga | Volume at price + HMA trend |
| EMA Ribbon Cloud | Multiple | Multi-EMA fan visualization |
| Session + Range [TFO] | TFO | Intraday range mapping |
| Kill Zone Levels | Multiple | ICT session-based S/R |

### Trending Themes (2026-06 Observation)
1. **Liquidity dominance**: Scripts that identify stop-hunt liquidity levels (equal highs/lows, sweep detection) are trending heavily — ICT concepts going mainstream
2. **Session-based context**: Killzone + range identification scripts overtook generic oscillators — traders want to know *which session* they're in, not just overbought/oversold
3. **HMA-based baselines**: Hull Moving Average as trend filter (faster than EMA, less lag) seen in BigBeluga, AlgoAlpha indicators. `ta.hma()` is the go-to for smooth trend baseline.
4. **Integrated dashboards**: Confluence indicators that combine 3-5 signals with a summary table/label (like our `AI TA Levels`) are trending — traders want one indicator, not ten.
5. **ML-adjacent visuals**: Nadaraya-Watson and kernel regression appearances in trending — readers perceive "ML" as edge even on public scripts

---

---

## 🧩 Advanced Pine Script v6 Patterns (from community source review)

These patterns were extracted from live source code of top community indicators and are ready to use in custom scripts.

### HMA Trend Baseline (BigBeluga — Tension Flow Trend)
```pine
// Hull Moving Average: smoother + faster response than EMA
hmaValue  = ta.hma(close, 50)
hmaSlopeUp = hmaValue > hmaValue[1]
```
Use `ta.hma()` as a baseline instead of EMA when you want faster trend detection with less whipsaw.

### Z-Score Overextension (BigBeluga)
```pine
// How many standard deviations price is stretched from HMA
priceDist = close - hmaValue
stdDev    = ta.stdev(priceDist, 50)
zScore    = priceDist / stdDev
absZ      = math.abs(zScore)

// > 2.0 = overextended (high-probability mean-reversion zone)
isOverextended = absZ > 2.0
```
Use Z-Score to identify when price is "too far" from trend baseline — complement to ATR-based channels.

### Dynamic Transparency (BigBeluga)
```pine
// More transparent when close to baseline; more opaque when extended
dynamicTransp = math.min(90, math.max(10, absZ * 25))
fill(p1, p2, top, mid, color.new(fillColor, 80 - dynamicTransp), color.new(fillColor, 100))
```
Ribbon becomes more visible as price stretches — visual overextension signal without a separate indicator pane.

### Signal Cooldown (BigBeluga)
```pine
// Prevent multiple signals from firing on consecutive bars
var int lastSignalBar = -100
canTrigger = (bar_index - lastSignalBar) >= signalGap  // e.g. signalGap = 30

bullSignal = hmaSlopeUp and ta.crossover(close, hmaValue) and canTrigger
if bullSignal or bearSignal
    lastSignalBar := bar_index
```
Essential for any signal-based indicator: prevents cluster signals at the same breakout candle.

### Active Trade Box Tracking (BigBeluga)
```pine
// Track multiple open boxes with parallel arrays
var activeSLBoxes = array.new_box()
var activeTPBoxes = array.new_box()
var entryPrices   = array.new_float()
var slPrices      = array.new_float()
var directions    = array.new_int()

// On each bar, extend box right and check for TP/SL hit
for i = array.size(activeSLBoxes) - 1 to 0
    box.set_right(array.get(activeSLBoxes, i), bar_index)
    bool hitSL = d == 1 ? low <= sL : high >= sL
    if hitSL or hitTP
        // Remove from tracking arrays by index
        array.remove(activeSLBoxes, i)
```
Use parallel arrays (indexed together) to track multiple live objects. Iterate backwards when removing to avoid index shift bugs.

### Rolling History Array (BigBeluga)
```pine
// Fixed-size array — push new, shift old when over maxSize
var tradeHistory = array.new_bool()
array.push(tradeHistory, hitTP)
if array.size(tradeHistory) > maxTrades
    array.shift(tradeHistory)
```
Same pattern used in SMC [LuxAlgo] for OB/FVG arrays. `array.shift()` removes index 0 (oldest).

### Session Killzone Detection (TFO — ICT Killzones)
```pine
// input.session() defines a time range; time() returns na if outside, bar_time if inside
london_session = input.session("0200-0500", "London", defval=true)
in_london      = not na(time(timeframe.period, london_session, "America/New_York"))

// Guard against drawing on higher timeframes
valid_tf = timeframe.in_seconds('') <= timeframe.in_seconds('60')
```

### Pivot H/L Per Session (TFO)
```pine
pivot_len = input.int(5, "Pivot Length")
ph = ta.pivothigh(high, pivot_len, pivot_len)
pl = ta.pivotlow(low, pivot_len, pivot_len)
// na when no pivot; non-na when pivot detected (offset pivot_len bars back)
```
Combine with session detection to find the highest high / lowest low within each killzone.

### Multi-Signal Confluence Enable/Disable (LuxAlgo — Signal Forge)
```pine
// Each signal source is independently toggleable
use_rsi    = input.bool(true, "RSI Signal",    group="Signals")
use_macd   = input.bool(true, "MACD Signal",   group="Signals")
use_bb     = input.bool(true, "BB Signal",     group="Signals")
use_volume = input.bool(true, "Volume Signal", group="Signals")

// Confluence count
bullCount = (use_rsi and rsi_bull ? 1 : 0) + (use_macd and macd_bull ? 1 : 0) + ...
bullSignal = bullCount >= minConfluence  // e.g. minConfluence = 2
```
Modular enable/disable allows users to tune which signals contribute to confluence.

### ATR-Based TP/SL/Trailing Stop (LuxAlgo — Signal Forge)
```pine
atr_mult_sl = input.float(1.5, "SL ATR Mult")
atr_mult_tp = input.float(3.0, "TP ATR Mult")

sl_price = entry - ta.atr(14) * atr_mult_sl  // for long
tp_price = entry + ta.atr(14) * atr_mult_tp

// Trailing stop: ratchet up as price advances
var float trail = na
trail := ta.highest(close, trail_len) - ta.atr(14) * trail_mult
```

### PA Toolkit UDT Pattern (UAlgo — PA Toolkit Lite)
```pine
// User-Defined Types (v5/v6) for clean data structures
type Box
    box   b
    float top
    float bot
    int   left
    bool  active

// Method syntax on UDTs
method update(Box self) =>
    box.set_right(self.b, bar_index)
```
UDTs keep box/line state organized without parallel arrays. Available in v5+.

### ZigZag via Pivots (UAlgo — PA Toolkit Lite)
```pine
// Pivot detection with lookback
ph = ta.pivothigh(high, zz_len, zz_len)
pl = ta.pivotlow(low, zz_len, zz_len)

// Trend direction from last two pivots
var float last_ph = na
var float last_pl = na
var int   trend   = 0  // 1 = uptrend, -1 = downtrend

if not na(ph)
    last_ph := ph
    trend   := last_ph > nz(last_ph[1]) ? 1 : -1
```

---

## 📚 Community Reference Library (Saved Sources)

Sources in `plugins/tradingview/assets/pinescript-indicators/community-reference/`:

| File | Author | License | Lines | Key Patterns |
|------|--------|---------|-------|--------------|
| `tension-flow-trend-bigbeluga.pine` | BigBeluga | CC BY-NC-SA 4.0 | 231 | HMA, Z-Score, signal cooldown, box tracking, win-rate table |
| `ict-killzones-pivots-tfo.pine` | TFO | Mozilla PL 2.0 | 723 | `input.session()`, pivot H/L per session, `timeframe.in_seconds()` |
| `signal-forge-luxalgo.pine` | LuxAlgo | CC BY-NC-SA 4.0 | 727 | Multi-signal confluence, ATR TP/SL/trailing, enable/disable toggles |
| `pa-toolkit-lite-ualgo.pine` | UAlgo | CC BY-NC-SA 4.0 | 300+ | UDTs, ZigZag, `box.new()` with `xloc.bar_time`, max-size array shift |

**Note:** All four sources are open (CC BY-NC-SA 4.0 or MPL 2.0). Non-commercial use + attribution required for CC sources.

---

## 📈 Core Built-in Technical Indicators

### 11. Relative Strength Index (RSI)
* **Description:** Momentum oscillator measuring the speed and change of price movements (Scale 0-100).
* **Summary:** Over 70 is overbought, under 30 is oversold. Divergences against price are key signals.

### 12. Moving Average Convergence Divergence (MACD)
* **Description:** Trend-following momentum indicator showing the relationship between two moving averages (usually 12 EMA and 26 EMA).
* **Summary:** Crossovers and histogram flips indicate momentum shifts. 

### 13. Bollinger Bands (BB)
* **Description:** A simple moving average (SMA) with an upper and lower band calculating standard deviations.
* **Summary:** Measures volatility. Price touching bands indicates extreme levels. Contraction indicates impending volatility.

### 14. Volume Profile Visible Range (VPVR)
* **Description:** Displays trading activity over a specified time period at specified price levels.
* **Summary:** Identifies the Point of Control (POC) and high/low volume nodes, acting as powerful support/resistance.

### 15. Exponential Moving Average (EMA)
* **Description:** A moving average that places a greater weight and significance on the most recent data points.
* **Summary:** Reacts faster to recent price changes than the SMA. 

### 16. Average True Range (ATR)
* **Description:** Measures market volatility by decomposing the entire range of an asset price for that period.
* **Summary:** Used strictly for measuring volatility to set stop-losses or position sizes, not trend direction.

### 17. Stochastic Oscillator
* **Description:** Momentum indicator comparing a particular closing price to a range of prices over a certain period.
* **Summary:** High sensitivity to market movements. Generates overbought/oversold signals (80/20 levels).

### 18. Ichimoku Cloud
* **Description:** A comprehensive indicator that defines support and resistance, identifies trend direction, gauges momentum, and provides trading signals.
* **Summary:** Price above the "cloud" is bullish, below is bearish. 

### 19. Fibonacci Retracement
* **Description:** Horizontal lines indicating where support and resistance are likely to occur based on Fibonacci numbers (0.236, 0.382, 0.5, 0.618).
* **Summary:** Used to predict pullback levels in an established trend.

### 20. Volume Weighted Average Price (VWAP)
* **Description:** The average price a security has traded at throughout the day, based on both volume and price.
* **Summary:** The benchmark for institutional intraday trading. Used to determine if you are buying at a premium or discount for the day.

---

## 🔍 Advanced / Niche Community Indicators

### 21. Williams %R [Built-in]
* **Description:** A momentum indicator that is the inverse of the Fast Stochastic Oscillator.
* **Summary:** Reflects the level of the close relative to the highest high for the look-back period.

### 22. Keltner Channels [Built-in]
* **Description:** Volatility-based envelopes set above and below an exponential moving average.
* **Summary:** Similar to Bollinger Bands but uses ATR instead of standard deviation.

### 23. ADX and DI [Built-in]
* **Description:** Average Directional Index. Used to quantify trend strength.
* **Summary:** ADX > 25 indicates a strong trend. +DI and -DI crossovers indicate direction.

### 24. Chaikin Money Flow (CMF) [Built-in]
* **Description:** Measures the amount of Money Flow Volume over a specific period.
* **Summary:** Buying pressure is indicated by positive CMF, selling by negative CMF.

### 25. Parabolic SAR [Built-in]
* **Description:** A time and price system used to determine the trailing stop and reverse points.
* **Summary:** Best used in trending markets. Not effective in sideways markets.

*(Note: This document compiles the highest-impact indicators for algorithmic integration. For a comprehensive script database, developers should utilize TradingView's Native Pine Script `ta.*` namespace and search community library functions.)*
