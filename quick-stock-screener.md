# Quick Stock Screener Framework
Key metrics to analyze stocks and generate an investment thesis, updated for enhanced precision, automation, adaptability, and insider trading insights.

## Introduction: Define Investment Horizon
- **Short-Term (1–2 years)**: Prioritize Revenue Growth, Price/Sales (P/S), and Free Cash Flow (FCF) trends.
- **Long-Term (5+ years)**: Emphasize Return on Invested Capital (ROIC), Competitive Moat, and Margin Expansion.
- **Step**: Specify your investment horizon to weight metrics appropriately in the scoring system.

## A. Revenue and Growth Analysis

### Key Measures
#### 1. Revenue Growth % Past
Evaluate historical revenue performance over 1–5 years, depending on data availability.

```formula
Revenue Growth % = (Current Revenue - Past Period Revenue) / Past Period Revenue
Revenue CAGR = [(Ending Revenue / Beginning Revenue)^(1/n)] - 1
where n = number of years
```

#### 2. Revenue Growth % Future
Assess future outlook using analyst projections from multiple sources.

- **Sources**: Cross-reference Yahoo Finance, Seeking Alpha, or Zacks for revenue estimates (e.g., https://finance.yahoo.com/quote/NVDA/analysis/).
- **Step**: Note the range of analyst estimates to gauge uncertainty (e.g., >10% variance indicates risk).

### Key Questions
- How does revenue growth compare to competitors’ growth (past and forecast)?
- Is the revenue growth trajectory stable, accelerating, or irregular?
- How does it compare to the industry median (source from Finviz or Morningstar)?
- Are analyst estimates consistent across sources?

## B. Operating Profitability Analysis

### Key Measures
#### 1. Operating Margin
Measures efficiency of core business operations before interest and taxes.

```formula
Operating Margin = Operating
