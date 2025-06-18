# Comprehensive Stock Screener Framework

This framework provides a structured approach to analyze stocks and generate an investment thesis, incorporating key financial metrics, recent news, investor call insights, and market sentiment indicators for precision, automation, adaptability, and insider trading insights.

## Introduction: Define Investment Horizon

- **Short-Term (1–2 years):** Prioritize Revenue Growth, Price/Sales (P/S), and Free Cash Flow (FCF) trends to capture near-term performance and valuation.
- **Long-Term (5+ years):** Emphasize Return on Invested Capital (ROIC), Competitive Moat, and Margin Expansion for sustainable value creation.
- **Step:** Specify investment horizon to weight metrics appropriately in the scoring system.

## A. Revenue and Growth Analysis

### Explanation
Revenue growth measures a company’s ability to increase sales over time, reflecting market demand and operational success. **High past growth (>20%)** indicates strong performance and market traction, often seen in growth stocks. **Low or negative growth (<5%)** signals stagnation or challenges, increasing risk. **Future growth projections** estimate potential based on analyst forecasts, with high variance (>10%) indicating uncertainty.

### Key Measures
1. **Revenue Growth % Past**:
   - Evaluates historical revenue performance over 1–5 years, depending on data availability.
   - **Formulas:**
     - Revenue Growth % = (Current Revenue - Past Period Revenue) / Past Period Revenue
     - Revenue CAGR = [(Ending Revenue / Beginning Revenue)^(1/n)] - 1, where n = number of years
2. **Revenue Growth % Future**:
   - Assesses future outlook using analyst projections from multiple sources (e.g., Yahoo Finance, Seeking Alpha, Zacks: https://finance.yahoo.com/quote/NVDA/analysis/).
   - **Step:** Note the range of analyst estimates to gauge uncertainty (e.g., >10% variance indicates risk).

### Key Questions
- How does revenue growth compare to competitors’ growth (past and forecast)?
- Is the revenue growth trajectory stable, accelerating, or irregular?
- How does it compare to the industry median (source: Finviz, Morningstar)?
- Are analyst estimates consistent across sources?

### Scoring
- **Past Growth**: >20%: 90; 5–20%: 60; <5%: 30
- **Future Growth**: >20%: 90; 5–20%: 60; <5%: 30

## B. Operating Profitability Analysis

### Explanation
Operating margin measures how efficiently a company converts revenue into operating profit before interest and taxes. **High margins (>20%)** indicate strong operational efficiency and pricing power, typical of mature or high-quality firms. **Low or negative margins (<10%)** suggest inefficiencies or heavy investment phases, common in growth companies.

### Key Measures
1. **Operating Margin**:
   - **Formulas:**
     - Operating Margin = Operating Income / Total Revenue
     - Adjusted Operating Margin = (Operating Income + Non-Recurring Expenses) / Revenue

### Analysis
- Compare past and current margins to assess trend.
- Compare to industry median (e.g., Finviz, Morningstar).
- For diversified firms, extract segment-level margins from SEC filings (10-K).

### Key Questions
- Is the company improving efficiency in turning sales into profits?
- Is it earning more profit per dollar of revenue compared to peers?
- Which company is the most efficient in the industry?

### Scoring
- >20%: 90; 10–20%: 60; <10%: 30

## C. Cash Flow Profitability Analysis

### Explanation
Free Cash Flow (FCF) measures cash generated after operating and capital expenses, reflecting financial health. **High FCF growth (>15%)** signals robust cash generation, supporting reinvestment or debt reduction. **Negative FCF** may be acceptable for growth firms if tied to strategic investments. **FCF Yield** compares cash flow to market valuation; **high yield (>5%)** indicates undervaluation, while **low yield (<2%)** suggests overvaluation.

### Key Measures
1. **Free Cash Flow (FCF) Growth Rate**:
   - **Formulas:**
     - FCF = Operating Cash Flow - Capital Expenditures (CAPEX)
     - FCF Growth Rate = (Current FCF - Previous FCF) / Previous FCF
2. **FCF Yield**:
   - **Formula:** FCF Yield = FCF / Market Cap

### Key Questions
- Is the company generating more cash relative to its size over time?
- How efficiently does it convert earnings to cash?
- Is FCF growth consistent and sustainable? If negative, is it due to strategic growth investments (e.g., data centers) with a clear path to positive FCF?

### Scoring
- **FCF Growth**: >15%: 90; 0–15%: 60; Negative: 30
- **FCF Yield**: >5%: 90; 2–5%: 60; <2%: 30

## D. Capital Efficiency Analysis

### Explanation
Return on Invested Capital (ROIC) measures how effectively a company uses capital to generate profits. **High ROIC (>15%)** indicates efficient capital allocation, creating value above the cost of capital (WACC). **Low ROIC (<8%)** suggests poor capital use, reducing long-term value. ROIC > WACC (e.g., 8–10% for tech) is a key threshold for efficiency.

### Key Measures
1. **Return on Invested Capital (ROIC)**:
   - **Formulas:**
     - ROIC = NOPAT / Invested Capital
     - NOPAT = Operating Income * (1 - Tax Rate)  # Default tax rate: 21% if unavailable
     - Invested Capital = Total Debt + Shareholders’ Equity - Cash and Equivalents
   - **Note:** Disclose assumptions (e.g., tax rate, cash estimates) if data is missing.
   - **Step:** Compare ROIC to Weighted Average Cost of Capital (WACC) using industry average (e.g., Tech: 8–10%).

### Key Questions
- Which company best turns capital into profit (highest ROIC)?
- Is ROIC growing efficiently compared to peers?

### Scoring
- >15%: 90; 8–15%: 60; <8%: 30

## E. Valuation Analysis

### Explanation
Valuation metrics assess whether a stock is over- or undervalued. **Price/Sales (P/S)** compares stock price to revenue; **low P/S (<5x for tech)** suggests undervaluation, while **high P/S (>10x)** indicates a premium, often justified by high growth. **PEG Ratio** adjusts P/E for growth; **<1.0** signals undervaluation relative to growth, while **>2.0** suggests overvaluation. **Forward P/E** uses future earnings; **low values (<15x for tech)** indicate undervaluation, while **high values (>30x)** reflect growth expectations.

### Key Measures
1. **Price/Sales (P/S) Ratio**:
   - **Formula:** P/S Ratio = Current Stock Price / Revenue per Share
2. **Price to Earnings Growth (PEG) Ratio**:
   - **Formula:** PEG Ratio = (Price/Earnings per Share) / Earnings Growth Rate (as whole number, e.g., 20 for 20%)
3. **Forward P/E**:
   - **Formula:** Forward P/E = Current Stock Price / Analyst EPS Estimate (Next 12 Months)

### Analysis
- Compare current P/S, PEG, and Forward P/E to industry medians and historical 3–5 year averages (source: Morningstar, Yahoo Finance).
- Check if valuation is justified by growth or other fundamentals.

### Key Questions
- How much are investors paying per dollar of sales compared to industry peers?
- Is a premium valuation warranted based on growth, margins, or moat?
- Is the stock over/undervalued relative to its historical averages?

### Scoring
- **P/S**: <5x: 90; 5–10x: 60; >10x: 30 (tech industry)
- **PEG**: <1.0: 90; 1.0–2.0: 60; >2.0: 30
- **Forward P/E**: <15x: 90; 15–30x: 60; >30x: 30 (tech industry)

## F. Balance Sheet Analysis

### Explanation
Balance sheet metrics assess financial stability. **Debt-to-Equity** measures leverage; **low ratios (<0.5)** indicate conservative financing, while **high ratios (>1.5)** signal risk. **Interest Coverage** shows debt serviceability; **>5x** is strong, while **<2x** raises concerns. **Current Ratio** evaluates liquidity; **>1.5** indicates ability to cover short-term liabilities, while **<1** suggests liquidity risks. **Net Debt** accounts for cash; negative net debt (cash > debt) is a strength.

### Key Measures
1. **Debt-to-Equity Ratio**:
   - **Formula:** Debt-to-Equity = Total Debt / Shareholders’ Equity
2. **Interest Coverage Ratio**:
   - **Formula:** Interest Coverage Ratio = EBIT / Interest Expense
3. **Current Ratio**:
   - **Formula:** Current Ratio = Current Assets / Current Liabilities
4. **Net Debt**:
   - **Formula:** Net Debt = Total Debt - Cash and Equivalents

### Key Questions
- How leveraged is the company compared to peers?
- Can it comfortably service its debt (Interest Coverage >5x)?
- Does a high cash balance mitigate debt concerns?
- Is short-term liquidity sufficient (Current Ratio >1)?

### Scoring
- **Debt-to-Equity**: <0.5: 90; 0.5–1.5: 60; >1.5: 30
- **Interest Coverage**: >5x: 90; 2–5x: 60; <2x: 30
- **Current Ratio**: >1.5: 90; 1–1.5: 60; <1: 30

## G. Competitive Advantage Analysis

### Explanation
Competitive moat assesses a company’s ability to sustain profits against competitors. **High moat (3+ factors)** indicates strong, sustainable advantages (e.g., brand, patents), reducing risk. **Low moat (0 factors)** suggests vulnerability to competition. Management quality evaluates execution; **strong track records** and **insider buying** signal confidence, while **heavy selling** or poor execution raises concerns. **High ESG scores** reflect sustainable practices, appealing to long-term investors.

### Key Measures
1. **Competitive Moat Assessment**:
   - **Brand Strength:** Market reputation and recognition.
   - **Network Effects:** Value increases with user base.
   - **Switching Costs:** Costs or barriers for customers to switch providers.
   - **Cost Advantages:** Lower operational costs than competitors.
   - **Intangible Assets:** Patents, licenses, proprietary tech (source: USPTO.gov).
   - **Moat Score:** High (3+ factors), Medium (1–2), Low (0).
2. **Management Quality**:
   - **Track Record of Execution:** Revenue growth, strategic pivots, or acquisitions.
   - **Capital Allocation History:** Efficiency of CAPEX, acquisitions, or buybacks.
   - **Insider Ownership Trends:** Percentage of shares held by insiders (source: SEC Form 3/4).
   - **Insider Trading Activity:** Summary of buying/selling from OpenInsider.com or SEC filings.
   - **Source:** http://openinsider.com/ for recent insider transactions.
   - **Analysis:** Calculate net insider buying/selling over the past 3–6 months (e.g., shares bought minus shares sold). Positive net buying signals confidence; heavy selling may indicate caution.
   - **ESG Rating:** Environmental, Social, Governance scores (source: MSCI, Sustainalytics).

### Key Questions
- What protects the business from competition?
- How sustainable are its competitive advantages?
- Does management’s track record, insider trading, and ESG performance support long-term value creation?
- Are insiders buying (bullish) or selling (bearish) significantly?

### Scoring
- **Moat**: High: 90; Medium: 60; Low: 30
- **Management/ESG**: Strong track record/positive insider buying/high ESG: 90; Mixed: 60; Weak/heavy selling/low ESG: 30

## H. Historical Trend Analysis

### Explanation
Historical trends evaluate performance consistency over time. **Strong revenue CAGR (>20%)** and **margin expansion** indicate improving fundamentals, while **deterioration** signals risks. **Cyclicality** assesses sensitivity to economic cycles; low volatility suggests stability, while high volatility indicates macro exposure.

### Key Measures
1. **Trends (1–5 Years)**:
   - Revenue CAGR (1–2 years for recent IPOs).
   - Margin expansion/contraction.
   - ROIC trajectory.
   - **Note:** For young companies (<5 years public), analyze 1–2 year trends or key milestones (e.g., IPO, major contracts).
2. **Cyclicality Assessment**:
   - Business cycle sensitivity.
   - Revenue volatility through economic cycles.
   - Macro impacts (e.g., interest rates, industry-specific regulations like AI privacy laws).

### Key Questions
- Is performance improving, stable, or deteriorating?
- How has the company performed during economic downturns?
- How do macro trends affect the company’s cyclicality?

### Scoring
- Improving: 90; Stable: 60; Deteriorating: 30

## I. Risk Assessment

### Explanation
Risk metrics gauge exposure to volatility and dependencies. **Beta** measures stock volatility; **>1** indicates higher market sensitivity, increasing risk, while **<1** suggests stability. **Customer concentration** assesses revenue reliance; **>50% from top clients** is high risk, while diversified revenue is safer.

### Key Measures
1. **Beta**:
   - **Formula:** Beta = Covariance(Stock Returns, Market Returns) / Variance(Market Returns)
2. **Customer Concentration**:
   - **Formula:** Customer Concentration = Revenue from Top Clients / Total Revenue

### Key Questions
- How exposed is the company to market swings (Beta >1 = high volatility)?
- Is revenue overly reliant on a few clients (>50% = high risk)?
- Are there regulatory risks (e.g., AI privacy laws, chip export controls)?

### Scoring
- **Beta**: <1: 90; 1–1.5: 60; >1.5: 30
- **Customer Concentration**: <20%: 90; 20–50%: 60; >50%: 30

## J. Peer Benchmarking

### Explanation
Compares the target company to peers to contextualize performance. Strong relative performance (e.g., higher growth, margins) suggests competitive strength, while underperformance highlights weaknesses.

- **Table Format:**

  | Metric            | [Company] | [Peer 1] | [Peer 2] | [Peer 3] |
  |-------------------|----------|----------|----------|----------|
  | Revenue Growth    |          |          |          |          |
  | Operating Margin  |          |          |          |          |
  | P/S Ratio         |          |          |          |          |
  | ROIC              |          |          |          |          |
  | Debt-to-Equity    |          |          |          |          |

- **Step:** Source peer data from Finviz, Yahoo Finance, or Morningstar. Select peers based on industry and market cap similarity.

## K. Recent News Summary

### Explanation
Recent news highlights strategic or financial developments. **Positive news** (e.g., partnerships, earnings beats) strengthens the investment case, while **negative news** (e.g., regulatory issues) increases risk. Market reactions (e.g., stock price moves) quantify impact.

### Key Measures
- Summarize major news from the past 1–3 months affecting the company’s outlook.
- **Sources:** Yahoo Finance, Reuters, TipRanks, or other reliable financial news platforms.
- **Focus Areas:**
  - Strategic moves (e.g., product launches, partnerships, acquisitions).
  - Financial updates (e.g., earnings surprises, guidance changes).
  - Market sentiment (e.g., analyst upgrades/downgrades, investor activity).
  - Macro or regulatory impacts (e.g., trade policies, industry trends).
- **Analysis:** Assess whether news strengthens or weakens the investment case. Quantify impact where possible (e.g., stock price movement post-news).

### Key Questions
- Does recent news indicate new growth opportunities or risks?
- How has the market reacted to these developments (e.g., stock price, options activity)?
- Are there recurring themes in news coverage (e.g., AI exposure, regulatory scrutiny)?

### Scoring
- Positive: 90; Neutral: 50; Negative: 10

## L. Investor Call Insights

### Explanation
Earnings calls reveal management’s priorities and analyst concerns. **Optimistic tone** aligned with strong financials signals confidence, while **cautious tone** or discrepancies suggest risks. Strategic shifts or guidance updates can impact outlook.

### Key Measures
- Summarize key discussions and questions from the most recent 1–2 earnings calls or investor presentations.
- **Sources:** Transcripts from company investor relations websites (e.g., investors.arm.com), Yahoo Finance, or Motley Fool.
- **Focus Areas:**
  - Strategic priorities (e.g., new markets, R&D focus).
  - Management’s outlook on growth, risks, or challenges.
  - Analyst questions on financials, competition, or macro factors.
  - Guidance updates and tone (optimistic, cautious, etc.).
- **Analysis:** Identify recurring themes or concerns raised by analysts. Note any discrepancies between management’s comments and financial data.

### Key Questions
- What are management’s key growth drivers and concerns?
- Are analysts focused on specific risks or opportunities (e.g., customer concentration, margin pressure)?
- Does management’s tone align with reported financials and market sentiment?
- Are there indications of strategic shifts or new initiatives?

### Scoring
- Optimistic: 90; Neutral: 50; Cautious: 10

## M. Short Float Analysis

### Explanation
**Short Float** measures the percentage of a company’s publicly tradable shares (float) sold short but not covered, reflecting bearish sentiment. **High short float (>20%)** indicates pessimism and potential for a short squeeze if positive catalysts emerge, driving volatility. **Low short float (<10%)** suggests bullish or neutral sentiment, reducing volatility. **Days to Cover** shows how long it takes short sellers to cover; **>5 days** increases squeeze risk.

### Key Measures
- **Short Float (%)**:
  - **Formula:** Short Float (%) = (Number of Shares Sold Short / Float) × 100
- **Days to Cover (Short Interest Ratio)**:
  - **Formula:** Days to Cover = Number of Shares Sold Short / Average Daily Trading Volume
- **Sources:** Short interest data from FINRA, NASDAQ, or platforms like Fintel.io, Finviz.com, updated bi-monthly.

### Analysis
- Compare short float to industry peers to assess relative bearish sentiment.
- Evaluate days to cover against historical trends (1–3 months).
- Check for catalysts (e.g., earnings, product launches) that could trigger a short squeeze.
- Monitor short borrow fee rates (via Fintel.io) for short-selling costs.

### Key Questions
- Is the short float high (>20%) or low (<10%) compared to industry peers?
- Does a high days-to-cover ratio (>5 days) suggest potential for a short squeeze?
- Are there upcoming catalysts (e.g., earnings, news) that could pressure short sellers?
- Do high short borrow fees indicate limited share availability, increasing squeeze risk?

### Scoring
- **Short Float**: >20%: 80 (high squeeze potential, volatile); 10–20%: 50 (moderate); <10%: 20 (low risk, stable).
- **Days to Cover**: >10 days: 80; 5–10 days: 50; <5 days: 20.

## N. Calls and Puts Open Interest Analysis

### Explanation
**Open Interest** tracks outstanding options contracts. **Calls** reflect bullish sentiment (buying the stock), while **puts** indicate bearish sentiment (selling the stock). A **high call/put ratio (>1.5)** suggests optimism, potentially amplifying upward moves, especially with high short float. A **low ratio (<0.7)** indicates bearish sentiment, reinforcing downward pressure. **% in Calls** shows bullishness; **>60%** is bullish, **<40%** is bearish.

### Key Measures
- **Call Open Interest**: Total outstanding call option contracts.
- **Put Open Interest**: Total outstanding put option contracts.
- **Call/Put Ratio**:
  - **Formula:** Call/Put Ratio = Call Open Interest / Put Open Interest
- **Percentage in Calls**:
  - **Formula:** % in Calls = (Call Open Interest / (Call Open Interest + Put Open Interest)) × 100
- **Sources:** Options data from CBOE, Yahoo Finance, or platforms like Barchart.com, updated daily.

### Analysis
- Compare call/put ratio to historical trends (1–3 months) to identify sentiment shifts.
- Assess open interest volume relative to average daily trading volume (e.g., >10% indicates strong activity).
- Check for unusual options activity (e.g., spikes) via Barchart.com or MarketChameleon.com.
- Correlate with short float: High call open interest with high short float may signal short squeeze potential.

### Key Questions
- Is the call/put ratio high (>1.5) or low (<0.7), indicating bullish or bearish sentiment?
- Does high call open interest align with low short float, suggesting bullish momentum?
- Is options activity significant relative to stock trading volume?
- Are there spikes in call or put open interest signaling potential catalysts?

### Scoring
- **Call/Put Ratio**: >1.5: 80 (bullish); 0.7–1.5: 50 (neutral); <0.7: 20 (bearish).
- **% in Calls**: >60%: 80; 40–60%: 50; <40%: 20.

## O. Scoring System

- Aggregate metrics into a final recommendation using a weighted scoring model.
- **Formula:**
  ```
  Score = (0.20 × Revenue Growth Score) + (0.15 × ROIC Score) + (0.15 × Valuation Score) + (0.15 × Margin Score) + (0.15 × FCF Score) + (0.10 × Balance Sheet Score) + (0.05 × News Impact Score) + (0.05 × Investor Call Sentiment Score) + (0.05 × Short Float Score) + (0.05 × Options Sentiment Score)
  ```
- **Scoring Guidelines:**
  - Strong Buy: >80
  - Consider: 50–80
  - Avoid: <50
- **Metric Scoring:** Assign 0–100 based on guideline fit (see Quick Reference Summary).
  - **News Impact Score:** 90 (positive), 50 (neutral), 10 (negative).
  - **Investor Call Sentiment Score:** 90 (optimistic), 50 (neutral), 10 (cautious).
  - **Short Float Score**: Average of Short Float and Days to Cover scores.
  - **Options Sentiment Score**: Average of Call/Put Ratio and % in Calls scores.


## Quick Reference Summary

| Metric                  | Strong Buy       | Consider         | Avoid           | Notes                                                                 |
|-------------------------|------------------|------------------|-----------------|----------------------------------------------------------------------|
| Revenue Growth (Past)   | >20%             | 5–20%            | <5%             | Compare to 3-5 year industry average & peers.                         |
| Revenue Growth (Future) | >20%             | 5–20%            | <5%             | Compare to analyst consensus and peers.                               |
| Operating Margin        | >20%             | 10–20%           | <10%            | Compare to industry median. Varies by sector.                         |
| FCF Growth              | >15%             | 0–15%            | Negative        | Negative FCF acceptable for growth firms.                             |
| FCF Yield               | >5%              | 2–5%             | <2%             | Compare to industry averages.                                         |
| ROIC                    | >15%             | 8–15%            | <8%             | Ensure ROIC > WACC. Capital-intensive sectors lower.                  |
| P/S Ratio               | <5x (Tech)       | 5–10x (Tech)     | >10x (Tech)     | Adjust for industry (e.g., Tech vs. Utilities).                       |
| PEG Ratio               | <1.0             | 1.0–2.0          | >2.0            | Best for growth stocks. Compare to peers.                             |
| Forward P/E             | <15x (Tech)      | 15–30x (Tech)    | >30x (Tech)     | Adjust for industry growth profiles.                                  |
| Debt-to-Equity          | <0.5             | 0.5–1.5          | >1.5            | Capital-intensive industries may have higher D/E.                     |
| Interest Coverage       | >5x              | 2–5x             | <2x             | Assess debt serviceability.                                           |
| Current Ratio           | >1.5             | 1–1.5            | <1              | Indicates liquidity strength.                                         |
| News Impact             | Positive         | Neutral          | Negative        | Based on strategic or financial impact of recent news.                |
| Investor Call Sentiment  | Optimistic       | Neutral          | Cautious        | Based on management tone and analyst questions.                       |
| Short Float             | <10%             | 10–20%           | >20%            | High short float signals squeeze potential but higher volatility.      |
| Days to Cover           | <5 days          | 5–10 days        | >10 days        | Higher days increase squeeze risk.                                    |
| Call/Put Ratio          | >1.5             | 0.7–1.5          | <0.7            | High ratio indicates bullish sentiment.                               |
| % in Calls              | >60%             | 40–60%           | <40%            | Higher % in calls suggests bullish options activity.                  |
