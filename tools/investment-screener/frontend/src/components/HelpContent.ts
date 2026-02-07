// Help content definitions for the investment screener
// Each key is a topic ID that can be referenced via HelpTrigger

export interface HelpTopic {
    title: string;
    summary: string;
    explanation: string;
    formula?: string;
    example?: string;
    learnMoreUrl?: string;
}

export const helpTopics: Record<string, HelpTopic> = {
    // Valuation Modeler terms
    growthRate: {
        title: "Revenue Growth Rate",
        summary: "The expected annual percentage increase in company revenue.",
        explanation: `Revenue growth rate measures how fast a company's sales are increasing year-over-year.

**The Law of Large Numbers:**
Yahoo's 1-year analyst estimate (e.g., 63% for NVDA) is NOT sustainable for 5 years! Consider:
- $130B growing at 63%/yr for 5 years = $1.5 TRILLION revenue
- That's larger than Apple's entire revenue today

**Common Growth Bottlenecks:**
- Memory constraints (HBM supply)
- Power limits (data center capacity)
- Manufacturing bottlenecks (TSMC/CoWoS)
- TAM saturation (only so many GPUs needed)

**Realistic Growth Curves:**
Most hypergrowth companies decelerate:
- Years 1-2: High growth (50-60%)
- Years 3-4: Moderation (25-35%)
- Year 5: Mature (15-20%)
- **5-Year CAGR: 35-45%** is more realistic than 63%

**Scenario Guidelines:**
- 🐻 Bear: 28-32% (faster maturation, competition)
- ⚖️ Base: 38-42% (controlled deceleration)
- 🐂 Bull: 48-55% (new TAMs, dominant position)`,
        formula: "CAGR = (Ending Revenue / Starting Revenue)^(1/Years) - 1",
        example: "NVDA: Bear 32%, Base 40%, Bull 50% accounts for inevitable slowdown from 63%",
        learnMoreUrl: "https://www.investopedia.com/terms/r/revenue-growth.asp"
    },

    netMargin: {
        title: "Net Profit Margin",
        summary: "The percentage of revenue that becomes profit after all expenses.",
        explanation: `Net margin shows how much of each dollar in revenue translates to actual profit after paying all costs (operations, taxes, interest, etc.).

Higher margins indicate better efficiency and pricing power. Tech companies often have higher margins (30-50%) than retail (2-5%).

In the valuation model, this converts projected revenue into projected earnings.`,
        formula: "Net Margin = Net Income / Revenue × 100",
        example: "If a company has $100B revenue and $55B net income, margin = 55B/100B × 100 = 55%",
        learnMoreUrl: "https://www.investopedia.com/terms/n/net_margin.asp"
    },

    exitPE: {
        title: "Exit P/E Multiple",
        summary: "The Price-to-Earnings ratio you expect the market to value the stock at in the future.",
        explanation: `The P/E ratio tells you how much investors are willing to pay for each dollar of earnings. A P/E of 30x means the stock price is 30 times its annual earnings.

**Why it matters for valuation:**
- Higher P/E = investors expect more future growth
- Lower P/E = mature companies or lower growth expectations
- Tech companies often trade at 25-60x P/E
- Value stocks trade at 10-20x P/E

**"Exit" P/E** is your estimate of what P/E the market will assign in 5 years.`,
        formula: "Stock Price = EPS × P/E Multiple",
        example: "If future EPS is $7.71 and you expect 30x P/E: Target Price = $7.71 × 30 = $231",
        learnMoreUrl: "https://www.investopedia.com/terms/p/price-earningsratio.asp"
    },

    shareChange: {
        title: "Share Count Change",
        summary: "Expected annual change in shares outstanding due to buybacks or dilution.",
        explanation: `Companies can change their share count over time:

**Buybacks (negative %):** Company purchases its own shares, reducing count. This increases EPS because earnings are split among fewer shares. Good for shareholders.

**Dilution (positive %):** New shares issued for acquisitions, employee compensation, or fundraising. This decreases EPS. Can be concerning if excessive.

Apple and Microsoft do significant buybacks (~3-5% annually). High-growth companies often issue shares.`,
        formula: "Future Shares = Current Shares × (1 + Share Change %)^Years",
        example: "If 2% annual buyback: After 5 years, shares = 100 × (1 - 0.02)^5 = 90.4 shares",
        learnMoreUrl: "https://www.investopedia.com/terms/s/sharerepurchase.asp"
    },

    // Analyst estimates
    forwardPE: {
        title: "Forward P/E Ratio",
        summary: "Current stock price divided by next year's expected earnings per share.",
        explanation: `Forward P/E uses analyst estimates for future earnings, unlike trailing P/E which uses past earnings.

**How to interpret:**
- Lower Forward P/E than Trailing P/E = earnings expected to grow
- Higher Forward P/E than Trailing P/E = earnings expected to decline

**Yahoo's Forward P/E** typically uses the current fiscal year EPS estimate.`,
        formula: "Forward P/E = Current Price / Estimated Future EPS",
        example: "NVDA at $185 with 2026 EPS estimate of $4.69: Forward P/E = 185/4.69 = 39.4x",
        learnMoreUrl: "https://www.investopedia.com/terms/f/forwardpe.asp"
    },

    epsEstimate: {
        title: "EPS Estimate",
        summary: "Analyst predictions for Earnings Per Share in future periods.",
        explanation: `Wall Street analysts publish estimates for how much profit per share a company will earn.

**Yahoo shows:**
- **Avg Estimate:** Consensus average of all analyst predictions
- **Low Estimate:** Most pessimistic analyst
- **High Estimate:** Most optimistic analyst
- **Year Ago EPS:** What the company actually earned last year

**Why it matters:** Companies that beat estimates often see stock price jumps. Missing estimates can cause drops.`,
        formula: "EPS = Net Income / Shares Outstanding",
        example: "2027 NVDA estimates: Low $6.17, Avg $7.71, High $9.68 per share",
        learnMoreUrl: "https://www.investopedia.com/terms/e/eps.asp"
    },

    targetPrice: {
        title: "Analyst Price Targets",
        summary: "Where analysts estimate the stock price will be in 12 months.",
        explanation: `Analysts publish 12-month price targets based on their valuation models.

**Yahoo shows:**
- **Low:** Most bearish analyst target
- **Mean/Average:** Consensus target
- **High:** Most bullish analyst target

**Important caveats:**
- These are opinions, not guarantees
- Analysts often update targets after earnings
- Targets cluster around current price (momentum bias)`,
        example: "NVDA targets: Low $140, Mean $254, High $352",
        learnMoreUrl: "https://www.investopedia.com/terms/p/price-target.asp"
    },

    // Expert Metrics
    ruleOf40: {
        title: "Rule of 40",
        summary: "A quick health check for growth companies: Revenue Growth % + Profit Margin % should exceed 40.",
        explanation: `The Rule of 40 balances growth vs. profitability. Companies can either:
- Grow fast with lower margins
- Grow slower with higher margins
- Or best: do both!

**Interpretation:**
- **Above 40:** Healthy balance, often valued higher
- **20-40:** Average, room for improvement
- **Below 20:** May need to choose: grow faster or become more profitable

Originally created for SaaS companies but now widely used for tech.`,
        formula: "Rule of 40 Score = Revenue Growth % + EBITDA (or Net) Margin %",
        example: "50% revenue growth + 30% margin = 80 score (excellent)",
        learnMoreUrl: "https://www.investopedia.com/terms/r/rule-of-40.asp"
    },

    piotroski: {
        title: "Piotroski F-Score",
        summary: "A 0-9 score measuring financial strength based on 9 accounting criteria.",
        explanation: `Created by Professor Joseph Piotroski, this score uses financial statements to identify strong vs. weak companies.

**The 9 criteria (1 point each):**
1. Positive ROA
2. Positive Operating Cash Flow
3. Rising ROA
4. Cash flow > Net Income (quality earnings)
5. Decreasing leverage (debt)
6. Improving liquidity (current ratio)
7. No share dilution
8. Improving gross margin
9. Improving asset turnover

**Interpretation:**
- **8-9:** Very strong fundamentals
- **5-7:** Average
- **0-4:** Weak, potential red flags`,
        learnMoreUrl: "https://www.investopedia.com/terms/p/piotroski-score.asp"
    },

    // Revenue estimates
    revenueEstimate: {
        title: "Revenue Estimates",
        summary: "Analyst predictions for total company sales in future periods.",
        explanation: `Similar to EPS estimates, analysts also predict revenue/sales.

**Why revenue matters:**
- Revenue is harder to manipulate than earnings
- Shows actual demand for products/services
- Growth companies are often valued on revenue (especially if not yet profitable)

**Yahoo shows ranges:** Low, Average, and High estimates for current and next year.`,
        formula: "Revenue = Total Sales (top line of income statement)",
        example: "NVDA 2026 revenue estimates: Low $203B, Avg $213B, High $216B",
        learnMoreUrl: "https://www.investopedia.com/terms/r/revenue.asp"
    },

    // New valuation inputs
    discountRate: {
        title: "Discount Rate (Required Return)",
        summary: "The annual return you require to justify the investment risk.",
        explanation: `The discount rate converts a future stock price into today's equivalent value. It answers: "What's this worth to me TODAY?"

**Why it matters:**
$500 in 5 years is NOT worth $500 today. You could invest that money elsewhere and earn returns.

**How to choose your rate:**
- **8%:** Aggressive / High risk tolerance (tech investor)
- **10%:** Typical market return expectation
- **12%:** Conservative / Lower risk tolerance
- **15%+:** Very high bar (Warren Buffett style)

**Higher discount rate = Lower present value.** If you require higher returns, you'll pay less today for the same future payoff.`,
        formula: "Present Value = Future Price / (1 + Discount Rate)^Years",
        example: "$500 in 5yr at 10% = $500 / 1.10^5 = $310 today",
        learnMoreUrl: "https://www.investopedia.com/terms/d/discountrate.asp"
    },

    timeHorizon: {
        title: "Time Horizon",
        summary: "How many years into the future you're projecting.",
        explanation: `The investment timeline for your valuation model.

**Considerations:**
- **3 years:** Short-term, less compounding, more speculative
- **5 years (default):** Standard for most DCF models
- **7-10 years:** Long-term, more compounding but more uncertainty

**Trade-offs:**
- Longer horizon = more growth compounding (good)
- Longer horizon = more uncertainty in estimates (risky)
- Longer horizon = more discounting (reduces present value)

Most analysts use 5-year projections as a balance between growth potential and forecast reliability.`,
        formula: "Future Value = Present Value × (1 + Growth Rate)^Years",
        example: "$100B revenue growing 30%/yr: In 5yr = $100B × 1.30^5 = $371B",
        learnMoreUrl: "https://www.investopedia.com/terms/t/timehorizon.asp"
    },
};
