# 0005: Technical Analysis Expert Sub-Agent & CDP Chart Controls

## Objective
Create a "Technical Trading Expert" sub-agent and the underlying TradingView CDP automation required to programmatically manipulate charts, manage indicators, and perform deep technical analysis to advise on entry/exit price levels.

## Context
While we currently have a `tv_ta_snapshot` skill that performs *visual* analysis of a chart screenshot, we need a dedicated persona that can actively drive the TradingView interface to gather specific data. This sub-agent will act as a seasoned technical analyst, utilizing both built-in TradingView indicators and custom Pine Script tools (developed in task #0004) to formulate actionable trading advice (Buy/Sell/Trim/Exit price levels).

## Required Capabilities

### 1. The Technical Analysis Sub-Agent Persona
- **Role:** Expert Technical Analyst.
- **Knowledge Base:** Deep understanding of moving averages (SMA, EMA, MACD), momentum oscillators (RSI, Stochastic), volume profiles, support/resistance clustering, Fibonacci retracements, and TradingView layouts.
- **Output:** Actionable advice on price levels for Initiating, Accumulating, Trimming, or Exiting positions.

### 2. CDP Chart Manipulation (Node.js/Python)
The agent requires a suite of new CDP tools within the `tradingview` plugin to actively manipulate the chart:
- **Change Timeframes:** Dynamically switch the chart resolution (e.g., 1D, 4H, 1H, 15m) to perform multi-timeframe analysis.
- **Manage Indicators:** Add and remove built-in indicators programmatically.
- **Data Extraction:** Read values directly from the TradingView "Data Window" (e.g., getting the exact current value of the 200 EMA or RSI) rather than relying solely on visual pixel analysis.

## Relationship to Other Tasks
- This task builds upon **Task #0004 (Pine Script Generation)**. The TA agent will use the Pine Script injector to load custom analysis scripts, extract the resulting data from the Data Window, and then clear the script to keep the chart clean.