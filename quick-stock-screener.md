# Quick stock screener framework
Key metrics to analyze stocks to generate an investment thesis.

## A. Revenue and Growth Analysis

### Key Measures
#### 1. Revenue Growth % Past
What has happened in the past?

``` formula
Revenue Growth % = (Current revenue - Past period revenue ) / Past period revenue
```

#### 2. Revenue Growth % Future

What is the future outlook? what is the revenue growth projected by analysts?
check yahoo finance revenue estimates  e.g. http://finance.yahoo.com/quote/NVDA/analysis/
   
### Key Questions:
* How does revenue growth compare to competitors' revenue growth?
    * Compare past trends and forecast trends (future).
    * Is the company's revenue growth trajectory (stable, accelerating, irregular)?
* How does it compare to others in the industry?

## B. Operating Profitability Analysis

### Key Measures
#### 1. Operating Margin
Operating Margin is a key profitability ratio that indicates how much profit a company makes from its operations before accounting for interest and taxes. It reflects the efficiency of a company's core business in generating profit from its revenue.

```formula
**Operating Margin** = Operating Income / Revenue (from the income statement)
**Operating Margin** = Operating Income / Total Revenue.
```

##### Analysis:
1.  Compare past to what it is now to know.
2.  Compare to the industry.

### Key Questions
* Is the company getting more (or less) efficient at turning sales into profits?
* Is the company earning more profits from each dollar of revenue?
* Which company is most efficient in the industry?

## C. Cash Flow Profitability Analysis

### Key measures

#### 1. Free Cash Flow (FCF) Growth Rate
Free Cash Flow (FCF) represents the cash a company generates after accounting for cash outflows to support its operations and maintain its capital assets. It's a crucial indicator of a company's financial health and its ability to generate cash for debt reduction, dividends, share buybacks, or future investments. Analyzing the growth rate of FCF provides insight into the company's expanding capacity to generate this valuable cash.

```formula
**FCF (Free Cash Flow)** = Operating Cash Flow - CAPEX (Capital Expenditures)
**FCF Growth Rate ** = (Current FCF - Previous FCF) / Previous FCF
```

### Key questions
* Is the company generating more cash relative to its size over time?
* How efficiently does the company convert earnings to cash?
* Is free cash flow growth consistent and sustainable?

## D. Capital Efficiency Analysis

### Key Measures

#### 1. Return on Invested Capital (ROIC)
Return on Invested Capital (ROIC) is a crucial profitability and efficiency metric that measures how effectively a company is using its invested capital to generate profits. It shows the percentage return that the company gains from the capital that has been invested by both bondholders and shareholders, indicating how efficiently a company generates cash. A higher ROIC generally suggests a more efficient and well-managed company.

**NOPAT (Net Operating Profit After Tax)** represents a company's potential cash earnings if its capitalization were entirely equity-financed.

```formula
**ROIC** = NOPAT / Invested Capital

**NOPAT** = Operating Income * (1 - Tax Rate)
# OR
**NOPAT** = pretax income - tax provision

**Invested Capital** = Net Working Capital + Net Operating Assets
# OR
**Invested Capital** = Current Assets - Current Liabilities + Property, Plant & Equipment + Intangible Assets
# OR (from balance sheet perspective)
**Invested Capital** = Total Assets - Non-Operating Assets
# OR (from financing perspective)
**Invested Capital** = Total Debt + Total Equity - Non-Operating Assets
```

e.g. 
| | | |
|---|---|---|
| pretax income | $ | 88,657,000 |
| tax provision | $ | 11,883,000 |
| **NOPAT** | **$** | **76,774,000** |
| Total Debt | $ | 8,463,000 |
| shareholders equity | $ | 79,327,000 |
| non operating assets | $ | 43,210,000 |
| **Invested Capital** | **$** | **44,580,000** |
| | | |
| ROIC | | 172% |

###  Key Questions:
* Which company is best at turning every dollar of capital into profit? (i.e. which company is getting the highest return on invested capital?)
* Which company is growing ROIC most efficiently?


## E. Valuation Analysis
you can't just look at AMD having a much lower number than NVDA.  Need  to consider all the other measures. 
Can look if it's cheaper relative to other periods etc.

### Key Measures

#### 1. Price/Sales
The Price/Sales (P/S) ratio is a valuation multiple that compares a company's stock price to its revenue. It indicates how much investors are willing to pay for each dollar of a company's sales. This ratio is particularly useful for valuing companies that are not yet profitable or have inconsistent earnings, as it relies on the top-line revenue rather than net income.

```formula
**Price/Sales Ratio** = Current Stock Price / Revenue per Share
```

#### 2. Price to Earnings Growth (PEG)
The Price to Earnings Growth (PEG) ratio is a widely used valuation metric that refines the traditional Price-to-Earnings (P/E) ratio by taking into account a company's earnings growth rate. It helps investors determine if a stock is overvalued or undervalued relative to its expected future earnings growth. A PEG ratio of 1 or less is generally considered fair value.

```formula
**PEG Ratio** = (Price/Earnings per Share) / Earnings Growth Rate (as a whole number, e.g., 20 for 20%)
```

###  Key Questions:
* how much are investors paying per dollar worth of sales for companies in the industry?
* are some companies worth a premium valuation based on other fundamentals like growth?

## F. Balance Sheet Analysis
### Key Measures
#### 1. Debt-to-Equity Ratio
```formula
Debt-to-Equity = Total Debt / Shareholders' Equity
```
#### 2. Interest Coverage Ratio
```formula
Interest Coverage Ratio = EBIT / Interest Expense
```

### Key questions
* How leveraged is the company compared to peers?
* Can the company comfortably service its debt?

## G. Competitive Advantage Analysis

### Key Measures
#### 1. Competitive Moat Assessment
- Brand strength
- Network effects
- Switching costs
- Cost advantages
- Intangible assets (patents, licenses)

#### 2. Management Quality
- Track record of execution
- Capital allocation history
- Insider ownership trends

### Key Questions:
* What protects this business from competition?
* How sustainable are the company's advantages?

## H. Historical Trend Analysis

### Key Measures
#### 1. Five-Year Trends
- Revenue CAGR
- Margin expansion/contraction
- ROIC trajectory

#### 2. Cyclicality Assessment
- Business cycle sensitivity
- Revenue volatility through economic cycles

### Key Questions:
* Is performance improving, stable, or deteriorating over time?
* How has the company performed during previous economic downturns?

## Quick Reference Summary

| Metric                | Strong Buy (General Guideline) | Consider (General Guideline) | Avoid (General Guideline) | How to Contextualize for Your Stocks |
|-----------------------|--------------------------------|------------------------------|---------------------------|--------------------------------------|
| Revenue Growth        | >15-20%                        | 5-15%                        | <5% (or declining)        | Compare to 3-5 year industry average & closest competitors (e.g., semiconductor growth vs. utility growth). |
| Operating Margin      | >20%                           | 10-20%                       | <10% (or negative)        | Compare to industry median and top performers in your sector. Software often has higher margins than hardware. |
| FCF Growth            | >15%                           | 0-15%                        | Negative/Inconsistent     | Look for consistent growth relative to industry peers; negative FCF can be normal for high-growth, reinvesting companies. |
| ROIC                  | >15%                           | 8-15%                        | <8%                       | Aim for ROIC > WACC. Compare to industry and competitors. Capital-intensive industries may have lower ROIC. |
| PEG Ratio             | <1.0                           | 1.0-1.5                      | >1.5 (or very high)       | Best used for growth stocks. Compare to peers with similar growth profiles. Lower is generally better. |
| Debt-to-Equity        | <0.5                           | 0.5-1.5  

*Note: These thresholds should be adjusted based on industry averages*

## Data Sources Reference

- SEC Filings (10-K, 10-Q): https://www.sec.gov/edgar/searchedgar/companysearch
- Yahoo Finance: https://finance.yahoo.com
- Finviz: https://finviz.com
- Seeking Alpha: https://seekingalpha.com
- Morningstar: https://www.morningstar.com

