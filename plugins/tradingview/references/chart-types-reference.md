# TradingView Chart Types & Readability Reference

## Overview
TradingView supports multiple native chart series styles. Choosing the appropriate style depends on indicator density, order flow requirements, and whether price or time is the primary analytical dimension.

---

## 1. Style Matrix & Indicator Compatibility

| Chart Style | TV UI Label | Type Category | Best Use Case | Readability with AI TA Overlay (EMA + Badges) |
|---|---|---|---|---|
| **Candles** | `Candles` | Time-based (OHLC) | Core analysis, pattern recognition, general charting | **High / Optimal** — Solid green/red bodies provide immediate momentum clarity without clashing with EMA colors. |
| **Hollow Candles** | `Hollow candles` | Time-based (OHLC) | Intraday price action vs. previous close | **Medium** — Hollow interiors can blend with dark theme backgrounds and grid lines when multiple EMAs are plotted. |
| **Bars** | `Bars` | Time-based (OHLC) | Clean minimal charting, heavy multi-indicator setups | **High** — Minimal screen footprint leaves maximum visibility for support/resistance lines and badges. |
| **Heikin Ashi** | `Heikin Ashi` | Synthetic Trend | Trend filtering and swing trade confirmation | **High** — Synthetic averaged bars eliminate noise; excellent for checking EMA slope alignment. |
| **Line / Step Line** | `Line` / `Step line` | Closing Price | Macro trend lines, portfolio benchmarking | **High** — Pure closing price curve; best when evaluating higher-timeframe DCF Fair Value crossings. |
| **Volume Footprint** | `Volume footprint` | Volume Microstructure | Intraday delta, aggressive bid/ask balance | **Low** — Internal volume histogram bars cover chart real estate, obscuring EMA lines and target badges. |
| **Session Volume Profile** | `Session volume profile` | Volume Distribution | Value Area (VAH/VAL/POC) identification | **Medium** — Useful for identifying key liquidity zones, but dense profiles reduce candle wick readability. |
| **Renko / Kagi / Point & Figure** | `Renko` / `Kagi` / `Point & figure` | Price-Only (Non-time) | Pure support/resistance breakout detection | **Specialized** — Time axis is removed; indicators computed on time intervals may behave differently. |

---

## 2. Recommendation Guidelines

1. **Default Screener & TA Layout**: Use standard **Solid Candlesticks** (`candle`) on Daily (`1D`) or `4h` timeframes. This ensures full visual fidelity for:
   - 21 / 50 / 200 EMA ribbons
   - Horizontal DCF Fair Value, Target Buy, and Trim levels
   - Previous Day High / Low levels
2. **Trend Confirmation Sweeps**: Switch temporarily to **Heikin Ashi** (`heikin-ashi`) during automated sweeps to evaluate trend persistence without local candle noise.
3. **Liquidity / Order Flow Deep Dives**: Use **Volume Footprint** (`volume-candle` / footprint) only during dedicated intraday execution analysis, then return to standard Candles for baseline persistence.

---

## 3. CDP Automation Notes

- **Header Dropdown**: The active chart style button in TradingView Desktop toolbar dynamically updates its `aria-label` / `title` to match the current style (e.g. `"Candles"`, `"Bars"`, `"Volume footprint"`).
- **Selector Path**: Always target the active toolbar button first to open the style menu, then click the target menu item (`[role="menuitem"]` or `[class*="item-"]`).
- **Layout Persistence**: Always invoke `chart saveLayout --name agent-layout` after modifying the style to ensure the preference persists across sessions.
