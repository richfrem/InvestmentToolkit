# Task 0005 Design: Technical Analysis Expert Sub-Agent & CDP Chart Controls

## 1. Overview
Create a "Technical Trading Expert" sub-agent and the underlying TradingView CDP automation required to programmatically manipulate charts, manage indicators, and perform deep technical analysis to advise on entry/exit price levels.

## 2. Architecture & Components

### 2.1 Technical Analysis Agent Persona
- **Location:** `.agents/skills/technical-analysis-expert/SKILL.md` (or similar)
- **Role:** Deep understanding of TA tools (MAs, RSI, MACD, volume, fib retracements).
- **Trigger:** `/tv-ta-deep {TICKER}`
- **Responsibilities:**
  1. Receive request for a ticker.
  2. Use CDP to navigate to ticker and desired timeframe (1D, 4H, etc).
  3. Load relevant built-in or custom Pine Script indicators via `pine-inject` skill (from Task 0004).
  4. Extract data from the Data Window.
  5. Clear custom indicators to keep the chart clean.
  6. Synthesize the extracted data to advise on Initiate/Accumulate/Trim/Exit price levels.

### 2.2 CDP Chart Manipulation Node Scripts
- **Location:** `plugins/tradingview/node/core/` and `cli.js`
- **New Capabilities:**
  - `changeTimeframe(client, resolution)`: Simulates typing a resolution (e.g., "1D", "60") or clicking the timeframe menu.
  - `manageBuiltInIndicators(client, action, name)`: Adds or removes built-in TV indicators.
  - `readDataWindow(client)`: Scrapes the current values of all active indicators from the Data Window using DOM traversal.

## 3. Data Flow
1. **User Request:** `Agent` -> `/tv-ta-deep AAPL`
2. **Chart Setup:** `Skill` uses Node CDP CLI to change ticker to AAPL, set timeframe to 1D.
3. **Indicator Setup:** `Skill` uses `pine-inject` to add custom script or `manageBuiltInIndicators` to add standard ones.
4. **Data Extraction:** `Skill` uses Node CDP CLI to read the Data Window.
5. **Synthesis:** LLM analyzes the JSON data and outputs trading advice.

## 4. Testing
- `tests/pine.test.js` (or similar) will mock CDP evaluations for the new chart controls to ensure success/failure handling.