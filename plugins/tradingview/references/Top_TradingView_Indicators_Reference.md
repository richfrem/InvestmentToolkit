# 📊 Top TradingView Indicators: AI Agent Reference Guide

**Purpose:** This document serves as an extended knowledge base for AI agents developing Pine Script v6 strategies. It covers the most popular built-in and community-developed indicators on TradingView, providing their core mechanics, use cases, and Pine Script implementation insights from live source-code review.

> **Source review tool:** `python3 plugins/tradingview/skills/author-pine-script/scripts/pine_source_reader.py --name "<indicator name>"`
> Saves source to `temp/indicator_sources/<Name>.pine` for detailed inspection.

---

## 🏆 Verified TV Popularity Ranking (as of 2026-05)

| Rank | Indicator | Pine Version | Key Pattern |
|------|-----------|-------------|-------------|
| 1 | Smart Money Concepts [LuxAlgo] | v5 | Box/line arrays, `var` for OBs, `ta.pivothigh/low` |
| 2 | Squeeze Momentum [LazyBear] | v4/v1 | BB inside KC = squeeze; `nz()` for momentum history |
| 3 | MacD Custom Indicator [ChrisMoody] | v1 | Color-coded histogram; `study()` (legacy) |
| 4 | SuperTrend [KivancOzbilgic] | v4 | ATR-based trailing stop; `ta.atr()` pattern |
| 5 | CM Williams Vix Fix | v1 | WVF = highest(close,22)-low / highest(close,22) |
| 6 | WaveTrend Oscillator [LazyBear] | v1 | EMA of HLCC/3, smoothed CI oscillator |
| 7 | S&R Levels with Breaks [LuxAlgo] | v5 | `var` line arrays; pivot-based S/R |
| 8 | Market Structure Break & OB [EmreKb] | v5 | BOS/CHoCH detection via swing highs/lows |
| 9 | UT Bot Alerts | v4 | ATR trailing stop with cross signals |
| 10 | Nadaraya-Watson Envelope [LuxAlgo] | v5 | Rational quadratic kernel; repaints on repaint=true |

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

### 10. Nadaraya-Watson Envelope [LuxAlgo] — RANK #10
* **Pine version:** v5
* **Key insight:** Uses rational quadratic kernel for non-parametric regression. The envelope **repaints by design** on the non-repainting=false setting. If using as a signal, always set `repainting=false` and use `[1]` offsets.

---

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
