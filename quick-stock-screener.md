# The Definitive Professional Investment Framework (v3.0)

## Guiding Philosophy: From Screener to Thesis
This framework is a systematic process for moving from a broad quantitative screen to a high-conviction investment thesis. It is built on three pillars of professional analysis:
1. **Variant Perception**: Identify a unique, evidence-backed belief that the market is missing or under-appreciating to drive alpha.
2. **Inflection Points & Rate of Change**: Focus on the trajectory (second derivative) of key metrics to capture businesses at inflection points.
3. **Asymmetric Risk/Reward**: Seek opportunities where the potential upside significantly outweighs the downside if the thesis is correct.

---

## Phase 0: Top-Down Strategic Overlay
*Define the macro and sector context before analyzing companies.*

1. **Macro Environment Assessment**:
   - **Interest Rates & Inflation**: High rates favor profitable firms; low rates fuel growth. Assess current conditions.
   - **Economic Cycle**: Expansion, slowdown, or recession? Impacts cyclical (Chips, Infra) vs. defensive (Cybersecurity) sectors.
   - **Geopolitical Climate**: Note risks like chip export controls, energy security policies, or supply chain disruptions.
2. **Sector Thesis Definition**: The primary focus is on high-growth sectors driven by AI, including chips/GPUs, data centers, robotics, cybersecurity, and power for data centers (e.g., nuclear energy plays like VST and OKLO). These sectors are prioritized due to increasing demand for AI-driven solutions, digital infrastructure, and sustainable energy, targeting companies with >20% revenue growth CAGR for 2025–2028 and Rule of 40 compliance.
3. **Framework Adjustment**: Adjust metric weightings based on macro conditions.
   - *Example*: "In a high-rate environment, emphasize SBC-Adjusted FCF, low Debt/EBITDA, and strong ROIIC."

### Sector-Specific Metric Thresholds
| Metric                | SaaS/Cyber | Chips/AI | Energy/Infra | Notes |
|-----------------------|------------|----------|--------------|-------|
| Gross Margin          | >75%       | 50–65%   | 30–45%       | Reflects sector profitability norms |
| Rule of 40            | >40%       | >30%     | >20%         | Lower for capital-intensive sectors |
| Debt/EBITDA           | <2x        | <2.5x    | <3x          | Energy/Infra allows higher leverage |
| Revenue Growth (Future)| >20%       | >15%     | >10%         | High-growth focus for SaaS/Cyber |
| EV/Sales (Fwd)        | <10x       | <8x      | <3x          | Capital-structure neutral |
| ROIC                  | >15%       | >12%     | >8%          | Lower for capital-intensive sectors |
| SBC-Adj FCF Yield     | >5%        | >3%      | >2%          | Reflects cash flow expectations |
| NDR (SaaS/Cyber)      | >120%      | N/A      | N/A          | Key for subscription businesses |

---

## Phase 1: Comprehensive Data Analysis (The Upgraded Screener)
*Systematically evaluate a company and its peers for signals of quality and mispricing.*

### A. Revenue and Growth Analysis
*Pro-Level Lens*: Focus on the **rate of change**. Accelerating growth (e.g., 10% to 15%) is more compelling than decelerating growth (e.g., 40% to 30%).

- **Forward-Looking & Quality Indicators (Sector-Specific)**:
  - **SaaS/Cybersecurity**: Net Dollar Retention (NDR), Gross Retention Rate (GRR), Remaining Performance Obligation (RPO) Growth, Average Contract Length.
  - **Infra/Energy**: Backlog Growth, Book-to-Bill Ratio, Capex Efficiency (Revenue Growth / Capex).
  - **Tech/AI**: R&D as % of Revenue (innovation vs. maintenance spending).
- **Key Measures**:
  1. **Revenue Growth % Past**:
     ```formula
     Revenue Growth % = (Current Revenue - Past Period Revenue) / Past Period Revenue
     Revenue CAGR = [(Ending Revenue / Beginning Revenue)^(1/n)] - 1
     where n = number of years
     ```
  2. **Revenue Growth % Future**:
     - **Sources**: Cross-reference Yahoo Finance, Seeking Alpha, Zacks, or company guidance (e.g., https://finance.yahoo.com/quote/NVDA/analysis/).
     - **Analysis**: Target >20% CAGR for 2025–2028. Note analyst estimate variance (>10% = high risk).
- **Key Questions**:
  - How does revenue growth compare to competitors in AI, chips, data centers, robotics, cybersecurity, or power sectors?
  - Is the growth trajectory stable, accelerating, or decelerating?
  - How does it compare to the industry median (source: Finviz, Morningstar)?
  - Are analyst estimates consistent and aligned with >20% CAGR?

### B. Rule of 40 Analysis
*Pro-Level Lens*: Analyze the trend of Rule of 40 components. Improving from 25% to 38% is better than dropping from 55% to 45%. Is FCF margin improving?

- **Key Measures**:
  ```formula
  Rule of 40 Score = Revenue Growth % (TTM or Fwd) + FCF Margin %
  FCF Margin % = Free Cash Flow / Total Revenue
  ```
  - **Thresholds**: >40% (SaaS/Cyber), >30% (Chips/AI), >20% (Energy/Infra).
  - **Sources**: Financial statements, SEC filings (10-K, 10-Q), analyst reports.
- **Key Questions**:
  - Does the company achieve a Rule of 40 score above sector-specific thresholds?
  - Is the balance between revenue growth and FCF margin sustainable or improving?
  - How does the Rule of 40 score and trend compare to industry peers?

### C. Operating Profitability Analysis
*Pro-Level Lens*: Focus on **margin trajectory**. Expanding margins signal operating leverage and pricing power.

- **Growth Efficiency (SaaS)**:
  - **Magic Number**: (Change in ARR * Gross Margin) / Sales & Marketing Spend
    - **Scoring**: >1 = 90, 0.5–1 = 60, <0.5 = 30
- **Key Measures**:
  1. **Operating Margin**:
     ```formula
     Operating Margin = Operating Income / Total Revenue
     Adjusted Operating Margin = (Operating Income + Non-Recurring Expenses) / Revenue
     ```
     - **Analysis**: Compare past and current margins. Extract segment-level margins from 10-K for diversified firms.
- **Key Questions**:
  - Is the company improving efficiency in turning sales into profits (margin expansion)?
  - Is it earning more profit per dollar of revenue compared to peers?
  - Which company is the most efficient in its industry?

### D. Cash Flow Profitability Analysis
*Pro-Level Lens*: Use **SBC-Adjusted FCF** to account for dilution in tech-heavy sectors.

- **Key Measures**:
  1. **SBC-Adjusted Free Cash Flow**:
     ```formula
     SBC-Adjusted FCF = Operating Cash Flow - Capex - Stock-Based Compensation
     ```
  2. **SBC-Adjusted FCF Yield**:
     ```formula
     SBC-Adjusted FCF Yield = SBC-Adjusted FCF / Market Cap
     ```
- **Key Questions**:
  - Is the company generating real cash (SBC-Adjusted FCF) relative to its size and peers?
  - Is the trend of SBC-Adjusted FCF positive or approaching an inflection point?
  - If FCF is negative, is it due to strategic investments (e.g., AI infrastructure, nuclear energy) with a clear path to positive FCF?

### E. Capital Efficiency Analysis
*Pro-Level Lens*: **ROIIC** predicts future value creation better than ROIC. Improving ROIIC signals effective capital allocation.

- **Key Measures**:
  1. **Return on Invested Capital (ROIC)**:
     ```formula
     ROIC = NOPAT / Invested Capital
     NOPAT = Operating Income * (1 - Tax Rate)  # Default tax rate: 21%
     Invested Capital = Total Debt + Shareholders’ Equity - Cash
     ```
  2. **Return on Incremental Invested Capital (ROIIC)**:
     ```formula
     ROIIC = (Change in NOPAT over 3–5 yrs) / (Total New Net Investment over 3–5 yrs)
     Total New Net Investment = (Change in Total Debt + Change in Equity + Retained Earnings - Dividends)
     ```
     - **Analysis**: ROIC > WACC (8–12%) indicates value creation. ROIIC > ROIC signals improving capital efficiency.
- **Key Questions**:
  - Which company best turns capital into profit (highest ROIC)?
  - Is ROIIC higher than ROIC, indicating improving capital allocation?

### F. Valuation Analysis
*Pro-Level Lens*: Use **EV multiples** (EV/Sales, EV/EBITDA) for capital-structure-neutral comparisons.

- **Key Measures**:
  1. **Enterprise Value**: Market Cap + Total Debt - Cash & Equivalents
  2. **EV/Sales Ratio**: EV / Total Revenue
  3. **EV/EBITDA Ratio**: EV / EBITDA
  4. **PEG Ratio**: (P/E) / Earnings Growth Rate
     - **Analysis**: Compare to industry medians and historical 3–5 year averages (source: Morningstar, Yahoo Finance).
- **Key Questions**:
  - How is the company valued on EV/Sales and EV/EBITDA compared to peers and historical ranges?
  - Is a premium valuation justified by superior growth, Rule of 40, or ROIIC?
  - What growth/profitability assumptions are baked into the current valuation?

### G. Balance Sheet Analysis
*Pro-Level Lens*: **Debt/EBITDA** is the key leverage metric, comparing debt to cash earnings.

- **Key Measures**:
  1. **Debt/EBITDA**: Total Debt / EBITDA
  2. **Net Debt**: Total Debt - Cash & Equivalents
  3. **Interest Coverage Ratio**: EBIT / Interest Expense
  4. **Current Ratio**: Current Assets / Current Liabilities
  5. **Debt-to-Equity**: Total Debt / Shareholders’ Equity
- **Key Questions**:
  - How leveraged is the company (Debt/EBITDA) compared to peers?
  - Can it service its debt (Interest Coverage >5x)?
  - Does a high cash balance mitigate debt concerns (Net Debt)?
  - Is short-term liquidity sufficient (Current Ratio >1.5)?

### H. Competitive Advantage & Management Quality Analysis
*Pro-Level Lens*: Develop conviction in the business’s durability and management’s skill.

- **Product/Platform Stickiness**:
  - **Net Dollar Retention (NDR)**: Revenue retained from existing customers, including upsells.
    ```formula
    NDR = (Revenue from Existing Customers at Period End / Revenue from Same Customers at Period Start) × 100
    ```
    - **Scoring**: >120% = 90, 100–120% = 60, <100% = 30
  - **Gross Retention Rate (GRR)**: Revenue retained excluding upsells.
    ```formula
    GRR = (Revenue from Existing Customers Excluding Upsells / Revenue from Same Customers at Period Start) × 100
    ```
    - **Scoring**: >90% = 90, 80–90% = 60, <80% = 30
  - **Churn Rate**: Percentage of customers or revenue lost.
    ```formula
    Churn Rate = (Lost Revenue or Customers / Total Revenue or Customers at Period Start) × 100
    ```
    - **Scoring**: <5% = 90, 5–10% = 60, >10% = 30
  - **Average Contract Length**: Duration of customer contracts.
    - **Scoring**: >2 years = 90, 1–2 years = 60, <1 year = 30
- **Competitive Moat Assessment**:
  - Brand Strength, Network Effects, Switching Costs, Cost Advantages, Intangible Assets (source: USPTO.gov).
  - **Key Question**: How is AI strengthening (e.g., data network effects) or threatening (e.g., automating services) the moat?
  - **Scoring**: High (3+ factors) = 90, Medium (1–2) = 60, Low (0) = 30
- **Management Quality**:
  - **Track Record & Execution**: Delivery on past promises.
  - **Capital Allocation**: High ROIIC, smart M&A, or buybacks.
  - **Insider Ownership & Trading**: Check OpenInsider for cluster buying/selling.
  - **ESG Rating**: Critical for Energy/Infra (source: MSCI, Sustainalytics).
  - **Earnings Call Analysis**: Assess tone, confidence, and consistency.
- **Key Questions**:
  - What protects the business from competition in AI, robotics, or power sectors?
  - How sustainable are its competitive advantages?
  - Does management’s track record, insider trading, and ESG performance support long-term value creation?

### I. Historical Trend & Cyclicality Analysis
*Pro-Level Lens*: Use historical trends to predict future behavior.

- **Key Measures**:
  - Trends (3–5 Years): Revenue CAGR, margin trajectory, ROIC, Rule of 40.
  - Cyclicality: Performance during downturns, sensitivity to interest rates or commodity prices.
- **Key Questions**:
  - Is performance improving, stable, or deteriorating?
  - How has the company performed during economic downturns?
  - How do macro trends (e.g., AI adoption, energy demand) affect cyclicality?

### J. Risk Assessment
*Pro-Level Lens*: Identify specific threats to your investment thesis.

- **Key Measures**:
  - **Beta**: Volatility relative to the market.
  - **Customer Concentration**: >20% from a single customer (source: 10-K).
  - **Dilution Risk**: Track shares outstanding.
  - **Geopolitical/Regulatory Risk**: AI privacy laws, chip export controls.
- **Key Questions**:
  - What are the top 3–5 risks that could break the investment thesis?
  - How exposed is the company to market swings (Beta)?
  - Is revenue overly reliant on a few clients?
  - Are there specific regulatory or geopolitical risks?

---

## Phase 2: Building the Thesis (Synthesis & Decision)

### 1. Define the Variant Perception
- **Market’s View (Consensus)**: Sentiment reflected in stock price and analyst reports.
- **Variant Perception (Thesis)**: What the market is missing (e.g., margin expansion from AI platform).
- **Key Catalysts / Why Now?**: Events in the next 6–18 months that will shift market perception.

### 2. Peer Benchmarking
*Visualize company standing with a “Trend/Rate of Change” column and Z-score/percentile.*

```template
| Metric                | [Company] | Trend/RoC | [Peer 1] | [Peer 2] | Peer Median |
|-----------------------|-----------|-----------|----------|----------|-------------|
| EV/Sales (Fwd)        |           |           |          |          |             |
| Revenue Growth (Fwd)  |           |           |          |          |             |
| SBC-Adj FCF Yield     |           |           |          |          |             |
| ROIC / ROIIC          |           |           |          |          |             |
| Debt/EBITDA           |           |           |          |          |             |
| NDR (SaaS/Cyber)      |           |           |          |          |             |
| Z-Score/Percentile    |           |           |          |          |             |
```

- **Step**: Source data from Finviz, Yahoo Finance, or Morningstar. Use Z-score (standard deviations from peer mean) or percentile rank for each metric.

### 3. Scenario Analysis & Asymmetry
- **Bull Case**: Price target if thesis plays out (e.g., +80% upside).
- **Base Case**: Price if consensus is correct (e.g., +10% upside).
- **Bear Case**: Price if risks materialize (e.g., -30% downside).
- **Conclusion**: Calculate asymmetric risk/reward ratio (e.g., 80% / 30% = 2.7-to-1).

### 4. Final Recommendation & Sell Discipline
- **Decision**: Buy, Hold, or Avoid based on variant perception and asymmetry.
- **Position Sizing**: Higher conviction and asymmetry = larger position.
- **Thesis Breakers**: 3 specific, measurable events to trigger a sale (e.g., NDR <115% for two quarters).

### 5. Scoring System (For Initial Screening)
```formula
Score = (0.25 × Revenue Growth Score) + (0.20 × Rule of 40 Score) + (0.15 × Operating Margin Score) + (0.10 × ROIC Score) + (0.10 × Valuation Score) + (0.10 × FCF Yield Score) + (0.05 × Balance Sheet Score) + (0.05 × Competitive Moat Score) + (0.05 × News Impact Score)
```
- **Scoring Guidelines**:
  - Strong Buy: >80
  - Consider: 50–80
  - Avoid: <50
- **Metric Scoring**:
  - Revenue Growth: >20% = 90, 5–20% = 60, <5% = 30
  - Rule of 40: >40% (SaaS/Cyber) or >30% (Chips/AI) or >20% (Energy/Infra) = 90, 30–40% (SaaS/Cyber) or 20–30% (Chips/AI) or 10–20% (Energy/Infra) = 60, <30% (SaaS/Cyber) or <20% (Chips/AI) or <10% (Energy/Infra) = 30
  - Operating Margin: >20% = 90, 10–20% = 60, <10% = 30
  - ROIC: >15% = 90, 8–15% = 60, <8% = 30
  - EV/Sales: <10x (SaaS/Cyber) or <8x (Chips/AI) or <3x (Energy/Infra) = 90, 10–15x (SaaS/Cyber) or 8–12x (Chips/AI) or 3–5x (Energy/Infra) = 60, >15x (SaaS/Cyber) or >12x (Chips/AI) or >5x (Energy/Infra) = 30
  - PEG Ratio: <1.0 = 90, 1.0–2.0 = 60, >2.0 = 30
  - SBC-Adj FCF Yield: >5% = 90, 2–5% = 60, <2% = 30
  - Debt/EBITDA: <2x (SaaS/Cyber) or <2.5x (Chips/AI) or <3x (Energy/Infra) = 90, 2–4x (SaaS/Cyber) or 2.5–4x (Chips/AI) or 3–5x (Energy/Infra) = 60, >4x (SaaS/Cyber) or >4x (Chips/AI) or >5x (Energy/Infra) = 30
  - Interest Coverage: >5x = 90, 2–5x = 60, <2x = 30
  - Current Ratio: >1.5 = 90, 1–1.5 = 60, <1 = 30
  - Competitive Moat: High = 90, Medium = 60, Low = 30
  - News Impact: Positive = 90, Neutral = 60, Negative = 30
  - NDR (SaaS/Cyber): >120% = 90, 100–120% = 60, <100% = 30
  - GRR (SaaS/Cyber): >90% = 90, 80–90% = 60, <80% = 30
  - Churn Rate: <5% = 90, 5–10% = 60, >10% = 30
  - Average Contract Length: >2 years = 90, 1–2 years = 60, <1 year = 30
- **Note**: Qualitative thesis (Phase 2) overrides quantitative score.

---

## Appendix A: Data Sources & Visualization
- **Data Sources**: Yahoo Finance (daily), SEC Filings (quarterly), Company IR (quarterly), OpenInsider (daily), Finviz (weekly), Morningstar (weekly), Sustainalytics (quarterly), MSCI (quarterly).
- **Visualization Enhancements**: Waterfall charts for FCF bridge, stacked bar for revenue by segment, bubble charts for growth vs. margin vs. valuation, Z-score/percentile for peer comparison.
- **Red Flags / Green Flags**:
  - **Red Flags**: Declining NDR, rising DSOs, management turnover, aggressive revenue recognition, large insider selling, declining gross margin, rising dilution.
  - **Green Flags**: Accelerating NDR, insider buying, new product launches, multi-year customer contracts, improving Rule of 40, margin expansion.

# Appendix B: Abbreviations
- **ARR**: Annual Recurring Revenue – Revenue from recurring subscriptions.
- **Book-to-Bill**: Ratio of orders received to revenue billed in a period.
- **CAGR**: Compound Annual Growth Rate.
- **Capex**: Capital Expenditures – Investments in fixed assets.
- **Churn Rate**: Percentage of customers or revenue lost in a period.
- **Current Ratio**: Current Assets divided by Current Liabilities.
- **Debt/EBITDA**: Total Debt divided by EBITDA, a leverage metric.
- **Debt-to-Equity**: Total Debt divided by Shareholders’ Equity.
- **DSO/DSOs**: Days Sales Outstanding – Average time to collect receivables.
- **EBITDA**: Earnings Before Interest, Taxes, Depreciation, and Amortization.
- **EV**: Enterprise Value – Market cap plus debt minus cash.
- **EV/Sales**: Enterprise Value divided by Total Revenue.
- **FCF**: Free Cash Flow – Cash from operations minus capital expenditures.
- **FCF Yield**: Free Cash Flow divided by Market Cap.
- **GRR**: Gross Retention Rate – Revenue retained from existing customers, excluding upsells.
- **Interest Coverage**: EBIT divided by Interest Expense.
- **Magic Number**: SaaS growth efficiency metric: (Change in ARR * Gross Margin) / Sales & Marketing Spend.
- **NDR**: Net Dollar Retention – Revenue retained from existing customers, including upsells.
- **Net Debt**: Total Debt minus Cash & Equivalents.
- **PEG**: Price/Earnings to Growth Ratio.
- **RPO**: Remaining Performance Obligation – Contracted revenue yet to be recognized.
- **ROIC**: Return on Invested Capital – Return on total invested capital.
- **ROIIC**: Return on Incremental Invested Capital – Return on new capital investments.
- **SBC**: Stock-Based Compensation – Non-cash compensation impacting FCF and dilution.
- **TTM**: Trailing Twelve Months.
- **WACC**: Weighted Average Cost of Capital – Average cost of equity and debt financing.
- **YoY**: Year-over-Year (annual growth comparison).
- **Z-score**: Standard deviations from the mean (used for peer comparison).