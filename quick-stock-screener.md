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
Operating Margin = Operating Income / Total Revenue
Adjusted Operating Margin = (Operating Income + Non-Recurring Expenses) / Revenue
```

##### Analysis
- Compare past and current margins to assess trend.
- Compare to industry median (e.g., Finviz, Morningstar).
- For diversified firms, extract segment-level margins from SEC filings (10-K).

### Key Questions
- Is the company improving efficiency in turning sales into profits?
- Is it earning more profit per dollar of revenue compared to peers?
- Which company is the most efficient in the industry?

## C. Cash Flow Profitability Analysis

### Key Measures
#### 1. Free Cash Flow (FCF) Growth Rate
Indicates cash available after operating and capital expenses.

```formula
FCF = Operating Cash Flow - Capital Expenditures (CAPEX)
FCF Growth Rate = (Current FCF - Previous FCF) / Previous FCF
```

#### 2. FCF Yield
Measures cash generation relative to market valuation.

```formula
FCF Yield = FCF / Market Cap
```

### Key Questions
- Is the company generating more cash relative to its size over time?
- How efficiently does it convert earnings to cash?
- Is FCF growth consistent and sustainable? If negative, is it due to strategic growth investments (e.g., data centers) with a clear path to positive FCF?

## D. Capital Efficiency Analysis

### Key Measures
#### 1. Return on Invested Capital (ROIC)
Measures efficiency of capital use to generate profits.

```formula
ROIC = NOPAT / Invested Capital
NOPAT = Operating Income * (1 - Tax Rate)  # Default tax rate: 21% if unavailable
Invested Capital = Total Debt + Shareholders’ Equity - Cash and Equivalents
```

- **Note**: If data is missing, disclose assumptions (e.g., tax rate, cash estimates).
- **Step**: Compare ROIC to Weighted Average Cost of Capital (WACC) using industry average (e.g., Tech: 8–10%). ROIC > WACC indicates efficient capital use.

### Key Questions
- Which company best turns capital into profit (highest ROIC)?
- Is ROIC growing efficiently compared to peers?

## E. Valuation Analysis

### Key Measures
#### 1. Price/Sales (P/S) Ratio
Compares stock price to revenue per share, useful for non-profitable firms.

```formula
P/S Ratio = Current Stock Price / Revenue per Share
```

#### 2. Price to Earnings Growth (PEG) Ratio
Refines P/E by factoring in earnings growth.

```formula
PEG Ratio = (Price/Earnings per Share) / Earnings Growth Rate (as whole number, e.g., 20 for 20%)
```

#### 3. Forward P/E
Assesses valuation based on expected future earnings.

```formula
Forward P/E = Current Stock Price / Analyst EPS Estimate (Next 12 Months)
```

##### Analysis
- Compare current P/S, PEG, and Forward P/E to industry medians and historical 3–5 year averages (source: Morningstar, Yahoo Finance).
- Check if valuation is justified by growth or other fundamentals.

### Key Questions
- How much are investors paying per dollar of sales compared to industry peers?
- Is a premium valuation warranted based on growth, margins, or moat?
- Is the stock over/undervalued relative to its historical averages?

## F. Balance Sheet Analysis

### Key Measures
#### 1. Debt-to-Equity Ratio
Measures financial leverage.

```formula
Debt-to-Equity = Total Debt / Shareholders’ Equity
```

#### 2. Interest Coverage Ratio
Assesses ability to service debt.

```formula
Interest Coverage Ratio = EBIT / Interest Expense
```

#### 3. Current Ratio
Evaluates short-term liquidity.

```formula
Current Ratio = Current Assets / Current Liabilities
```

#### 4. Net Debt
Accounts for cash reserves offsetting debt.

```formula
Net Debt = Total Debt - Cash and Equivalents
```

### Key Questions
- How leveraged is the company compared to peers?
- Can it comfortably service its debt (Interest Coverage >5x)?
- Does a high cash balance mitigate debt concerns?
- Is short-term liquidity sufficient (Current Ratio >1)?

## G. Competitive Advantage Analysis

### Key Measures
#### 1. Competitive Moat Assessment
- **Brand Strength**: Market reputation and recognition.
- **Network Effects**: Value increases with user base.
- **Switching Costs**: Costs or barriers for customers to switch providers.
- **Cost Advantages**: Lower operational costs than competitors.
- **Intangible Assets**: Patents, licenses, proprietary tech (source: USPTO.gov).
- **Moat Score**: High (3+ factors), Medium (1–2), Low (0).

#### 2. Management Quality
- **Track Record of Execution**: Revenue growth, strategic pivots, or acquisitions.
- **Capital Allocation History**: Efficiency of CAPEX, acquisitions, or buybacks.
- **Insider Ownership Trends**: Percentage of shares held by insiders (source: SEC Form 3/4).
- **Insider Trading Activity**: Summary of buying/selling from OpenInsider.com or SEC filings.
  - **Source**: http://openinsider.com/ for recent insider transactions.
  - **Analysis**: Calculate net insider buying/selling over the past 3–6 months (e.g., shares bought minus shares sold). Positive net buying signals confidence; heavy selling may indicate caution.
  - **Example**: For CoreWeave (CRWV), 17 sales vs. 1 purchase in 6 months (e.g., CEO sold ~$50M, one director bought $20M) suggests profit-taking post-IPO.[](https://www.nasdaq.com/articles/coreweave-earnings-preview-recent-crwv-insider-trading-hedge-fund-activity-and-more)[](https://www.nasdaq.com/articles/wednesday-5-14-insider-buying-report-crwv)
- **ESG Rating**: Environmental, Social, Governance scores (source: MSCI, Sustainalytics).

### Key Questions
- What protects the business from competition?
- How sustainable are its competitive advantages?
- Does management’s track record, insider trading, and ESG performance support long-term value creation?
- Are insiders buying (bullish) or selling (bearish) significantly?

## H. Historical Trend Analysis

### Key Measures
#### 1. Trends (1–5 Years)
- Revenue CAGR (1–2 years for recent IPOs).
- Margin expansion/contraction.
- ROIC trajectory.
- **Note**: For young companies (<5 years public), analyze 1–2 year trends or key milestones (e.g., IPO, major contracts).

#### 2. Cyclicality Assessment
- Business cycle sensitivity.
- Revenue volatility through economic cycles.
- Macro impacts (e.g., interest rates, industry-specific regulations like AI privacy laws).

### Key Questions
- Is performance improving, stable, or deteriorating?
- How has the company performed during economic downturns?
- How do macro trends affect the company’s cyclicality?

## I. Risk Assessment

### Key Measures
#### 1. Beta
Measures stock volatility relative to the market.

```formula
Beta = Covariance(Stock Returns, Market Returns) / Variance(Market Returns)
```

#### 2. Customer Concentration
Percentage of revenue from top 1–3 clients.

```formula
Customer Concentration = Revenue from Top Clients / Total Revenue
```

### Key Questions
- How exposed is the company to market swings (Beta >1 = high volatility)?
- Is revenue overly reliant on a few clients (>50% = high risk)?
- Are there regulatory risks (e.g., AI privacy laws, chip export controls)?

## J. Peer Benchmarking
Compare the target company to 3–5 peers on key metrics to contextualize performance.

```template
| Metric            | [Company] | [Peer 1] | [Peer 2] | [Peer 3] |
|-------------------|----------|----------|----------|----------|
| Revenue Growth    |          |          |          |          |
| Operating Margin  |          |          |          |          |
| P/S Ratio         |          |          |          |          |
| ROIC              |          |          |          |          |
| Debt-to-Equity    |          |          |          |          |
```

- **Step**: Source peer data from Finviz, Yahoo Finance, or Morningstar. Select peers based on industry and market cap similarity.

## K. Scoring System
Aggregate metrics into a final recommendation using a weighted scoring model.

```formula
Score = (0.3 × Revenue Growth Score) + (0.2 × ROIC Score) + (0.2 × Valuation Score) + (0.15 × Margin Score) + (0.15 × FCF Score) + (0.1 × Balance Sheet Score)
```

- **Scoring Guidelines**:
  - Strong Buy: >80
  - Consider: 50–80
  - Avoid: <50
- **Metric Scoring**: Assign 0–100 based on guideline fit (e.g., Revenue Growth >20% = 90, 5–15% = 60, <5% = 30).

## L. Visualization
Create charts to visualize trends for better decision-making.

- **Suggested Charts**:
  - Line chart: Revenue Growth and Margin over 1–5 years.
  - Bar chart: Compare ROIC, P/S, and Debt-to-Equity vs. peers.
- **Tools**: Use Chart.js, Excel, or Python (matplotlib) for plotting.
  ```python
  import matplotlib.pyplot as plt
  years = [2022, 2023, 2024]
  revenue = [15.8, 220, 1910]  # Example: CoreWeave revenue ($M)
  plt.plot(years, revenue)
  plt.title("Revenue Growth Trend")
  plt.show()
  ```

## Quick Reference Summary
| Metric                | Strong Buy | Consider       | Avoid          | Notes                              |
|-----------------------|------------|----------------|----------------|------------------------------------|
| Revenue Growth (Past) | >20%       | 5–20%         | <5%            | Compare to 3-5 year industry average & peers. |
| Revenue Growth (Future)| >20%       | 5–20%         | <5%            | Compare to analyst consensus and peers. |
| Operating Margin      | >20%       | 10–20%        | <10%           | Compare to industry median. Varies by sector. |
| FCF Growth            | >15%       | 0–15%         | Negative       | Negative FCF acceptable for growth firms. |
| FCF Yield             | >5%        | 2–5%          | <2%            | Compare to industry averages. |
| ROIC                  | >15%       | 8–15%         | <8%            | Ensure ROIC > WACC. Capital-intensive sectors lower. |
| P/S Ratio             | <5x (Tech) | 5–10x (Tech)  | >10x (Tech)    | Adjust for industry (e.g., Tech vs. Utilities). |
| PEG Ratio             | <1.0       | 1.0–2.0       | >2.0           | Best for growth stocks. Compare to peers. |
| Forward P/E           | <15x (Tech)| 15–30x (Tech) | >30x (Tech)    | Adjust for industry growth profiles. |
| Debt-to-Equity        | <0.5       | 0.5–1.5       | >1.5           | Capital-intensive industries may have higher D/E. |
| Interest Coverage     | >5x        | 2–5x          | <2x            | Assess debt serviceability. |
| Current Ratio         | >1.5       | 1–1.5         |
