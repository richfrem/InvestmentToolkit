# Reusable Stock Screening Prompt for Definitive Professional Investment Framework (v3.0)

## Purpose
This prompt is designed to apply the **Definitive Professional Investment Framework (v3.0)** (provided separately) to screen and rank companies listed on NASDAQ and Dow Jones in the AI, robotics, cybersecurity, chips/GPUs, data centers, power (e.g., nuclear energy), and sectors leveraging AI to transform business like RXRX and ISRG sectors. Secondary premise is companies very transformational and huge growth potential like Cathy Woods ARKK criteria.  It follows a systematic process to identify eligible companies, filter them based on the investment thesis, collect data, score and rank them, and synthesize investment theses, producing an ordered list of all qualifying companies with scores, variant perceptions, and thesis breakers.

## Instructions
- **Input Files**: the two provided files:
  1. **Definitive_Investment_Framework_v3.0.md**: The full investment framework with sector-specific thresholds, formulas, scoring system, and guidelines.
  2. This prompt (**Stock_Screening_Prompt.md**).
- **Output**: you will generate a Markdown file containing:
  - A ranked list of all companies meeting the investment thesis criteria (>20% revenue growth CAGR for 2025–2028 for SaaS/Cyber, >15% for Chips/AI, >10% for Energy/Infra; Rule of 40: >40% for SaaS/Cyber, >30% for Chips/AI, >20% for Energy/Infra).
  - Each company’s total score (per the framework’s scoring system), key strengths, variant perception, catalysts, and thesis breakers.
  - A peer benchmarking table for the top 5 companies.
  - No companies outside the specified sectors (e.g., healthcare like Gilead Sciences) or with insufficient data will be included.

## Steps to Apply the Framework
Follow these steps to execute the screening process, referencing the **Definitive Professional Investment Framework (v3.0)** for all metrics, thresholds, and scoring guidelines.

### 1. Identify Eligible Companies
- **Source**: Use NASDAQ and Dow Jones listings, focusing on companies in AI, robotics, cybersecurity, chips/GPUs, data centers, and power (e.g., nuclear energy like Vistra (VST), Oklo (OKLO)).
- **Indices**: Leverage the Nasdaq CTA Artificial Intelligence & Robotics Index (NQROBO) for AI/robotics companies and screen for cybersecurity (e.g., Cloudflare, Palantir) and power (e.g., Vistra, Constellation Energy) firms.
- **Example Companies**: Include, but are not limited to, NVIDIA, TSMC, Dell, Palantir, Cloudflare, Broadcom, Amazon, Alphabet, Tesla, Serve Robotics.
- **Action**: Compile a comprehensive list of companies in these sectors from NASDAQ and Dow Jones, using sources like indexes.nasdaqomx.com, finance.yahoo.com, or kiplinger.com.

### 2. Filter for Investment Thesis
- **Criteria**:
  - **Revenue Growth**: Target >20% CAGR for 2025–2028 (SaaS/Cyber), >15% (Chips/AI), >10% (Energy/Infra), per analyst projections or company guidance.
  - **Rule of 40**: >40% (SaaS/Cyber), >30% (Chips/AI), >20% (Energy/Infra), calculated as Revenue Growth % + FCF Margin %.
- **Exclusions**: Exclude companies:
  - Outside the specified sectors (e.g., healthcare like Gilead Sciences).
  - With insufficient data for revenue growth or Rule of 40 (e.g., missing analyst estimates or financials).
- **Action**: Apply filters using data from Yahoo Finance, SEC filings, or analyst reports to create a shortlist of qualifying companies.

### 3. Collect Data
- **Quantitative Metrics**: Per the framework, collect:
  - Revenue Growth (Past and Future), Rule of 40, SBC-Adjusted FCF, SBC-Adjusted FCF Yield, ROIC, ROIIC, EV/Sales, EV/EBITDA, PEG Ratio, Debt/EBITDA, Interest Coverage, Current Ratio, NDR (SaaS/Cyber), GRR, Churn Rate, Average Contract Length.
  - Sources: Yahoo Finance, SEC filings (10-K, 10-Q), analyst reports (e.g., Seeking Alpha, Zacks).
- **Qualitative Factors**: Assess:
  - **Competitive Moat**: Brand Strength, Network Effects, Switching Costs, Cost Advantages, Intangible Assets (e.g., patents from USPTO.gov).
  - **Management Quality**: Track record, insider ownership/trading (OpenInsider), ESG ratings (Sustainalytics, MSCI), earnings call tone (confidence, consistency).
- **Action**: Gather data for each shortlisted company, ensuring alignment with sector-specific thresholds in the framework.

### 4. Score and Rank
- **Scoring System**: Apply the framework’s scoring formula:
  ```formula
  Score = (0.25 × Revenue Growth Score) + (0.20 × Rule of 40 Score) + (0.15 × Operating Margin Score) + (0.10 × ROIC Score) + (0.10 × Valuation Score) + (0.10 × FCF Yield Score) + (0.05 × Balance Sheet Score) + (0.05 × Competitive Moat Score) + (0.05 × News Impact Score)
  ```
- **Metric Scoring**: Use the framework’s thresholds (e.g., Revenue Growth: >20% = 90, 5–20% = 60, <5% = 30; Debt/EBITDA: <2x (SaaS/Cyber) = 90).
- **Peer Benchmarking**: Calculate percentile ranks (0–100%) for each metric vs. 3–5 peers in the same sector.
- **Action**: Score each company, rank them by total score, and prioritize those with scores >80 (Strong Buy).

### 5. Synthesize Thesis
- **Variant Perception**:
  - **Market’s View**: Summarize consensus sentiment from stock price and analyst reports.
  - **Your Thesis**: Identify what the market misses (e.g., underestimating margin expansion from AI-driven products).
  - **Catalysts**: List 1–3 events (6–18 months) that could drive revaluation (e.g., earnings beats, new contracts).
- **Scenario Analysis**:
  - **Bull Case**: Price target if thesis is correct (e.g., +50% upside).
  - **Base Case**: Price if consensus is correct (e.g., +10% upside).
  - **Bear Case**: Price if risks materialize (e.g., -30% downside).
  - **Asymmetric Risk/Reward**: Calculate upside/downside ratio.
- **Thesis Breakers**: Define 3 specific, measurable events that would invalidate the thesis (e.g., “Revenue growth <10% for two quarters”).
- **Action**: Develop a concise thesis for each company, focusing on top-ranked candidates.

## Output Format
Generate a Markdown file with the following structure:

```markdown
# Stock Screening Results (Generated on [Current Date])

## Overview
- **Date**: [Insert current date, e.g., July 18, 2025]
- **Sectors**: AI, Robotics, Cybersecurity, Chips/GPUs, Data Centers, Power
- **Criteria**: Revenue Growth (>20% CAGR for SaaS/Cyber, >15% for Chips/AI, >10% for Energy/Infra), Rule of 40 (>40% for SaaS/Cyber, >30% for Chips/AI, >20% for Energy/Infra)
- **Source**: NASDAQ and Dow Jones listings, Nasdaq CTA Artificial Intelligence & Robotics Index (NQROBO), Yahoo Finance, SEC filings, OpenInsider, analyst reports

## Ranked List of Qualifying Companies
| Rank | Company | Ticker | Sector | Score | Key Strengths | Variant Perception | Catalysts | Thesis Breakers |
|------|---------|--------|--------|-------|---------------|-------------------|-----------|-----------------|
| 1    | [Company Name] | [Ticker] | [Sector] | [Score] | [e.g., High revenue growth, strong NDR] | [e.g., Market underestimates AI platform margins] | [e.g., Q3 earnings beat, new contracts] | [e.g., Revenue growth <10%, insider selling] |
| ...  | ...     | ...    | ...    | ...   | ...           | ...               | ...       | ...             |

## Peer Benchmarking (Top 5 Companies)
| Metric | [Company 1] | Trend/RoC | [Peer 1] | [Peer 2] | [Peer 3] | Peer Median | [Company 1] Percentile |
|--------|-------------|-----------|----------|----------|----------|-------------|-----------------------|
| EV/Sales (Fwd) | ... | ... | ... | ... | ... | ... | ... |
| Revenue Growth (Fwd) | ... | ... | ... | ... | ... | ... | ... |
| SBC-Adj FCF Yield | ... | ... | ... | ... | ... | ... | ... |
| ROIC / ROIIC | ... | ... | ... | ... | ... | ... | ... |
| Debt/EBITDA | ... | ... | ... | ... | ... | ... | ... |
| NDR (SaaS/Cyber) | ... | ... | ... | ... | ... | ... | ... |

## Notes
- **Data Gaps**: List any companies excluded due to insufficient data.
- **Assumptions**: Note any assumptions (e.g., tax rate for ROIC, analyst estimate ranges).
- **Sources**: Cite specific sources used (e.g., Yahoo Finance, SEC filings, OpenInsider).
```

## Notes
- **Data Sources**: Use Yahoo Finance, SEC filings (10-K, 10-Q), OpenInsider, Finviz, Morningstar, Sustainalytics, MSCI, and analyst reports (e.g., Seeking Alpha, Zacks) for data collection.
- **Automation**: If data volume is large, suggest using a Python script with pandas to automate scoring and ranking.
- **Qualitative Analysis**: Listen to earnings calls for management tone and cross-check insider trading on OpenInsider for cluster buying/selling signals.
- **Error Handling**: If data is unavailable (e.g., missing analyst estimates), exclude the company and note the reason in the output.