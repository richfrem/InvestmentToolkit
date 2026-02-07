# Feature Specification: Investment Screener

## 1. Overview
### Goal
Create a premium, dark-mode "**Investment Analyzer & Screener**" web application inspired by the "1000x Stocks" aesthetic. The tool will provide deep fundamental analysis, visual charting, stock comparison, and valuation modeling (Bull/Base/Bear cases), specifically targeting users who need high-quality financial data without expensive Bloomberg terminal subscriptions.

### Core Value Proposition
- **Premium User Experience**: A "Luxury Dark Mode" interface (Black/Gold theme) that feels professional and exclusive.
- **Deep Fundamental Analysis**: Access to key metrics like PEG Ratio, Piotroski F-Score, and Insider Ownership that are often paywalled.
- **Valuation Modeling**: An interactive "Valuation Scenario Modeler" that allows users to project 5-year returns based on their own assumptions (Revenue Growth, Net Margins, PE Multiples).
- **Comparative Analysis**: A side-by-side screener to compare multiple tickers (e.g., NVDA vs AMD) on key metrics to identify the best value.

## 2. User Stories
### Primary Actor: The Retail Investor
- **As a** sophisticated retail investor,
- **I want** to quickly analyze a stock's fundamental health using advanced metrics (PEG, Piotroski),
- **So that** I can filter out low-quality companies and focus on high-potential investments.

### User Scenarios
1.  **Quick Health Check**:
    - User searches for a ticker (e.g., "PLTR").
    - User instantly sees the "Expert Metrics" panel with PEG Ratio, Piotroski Score, and Insider Ownership.
    - User glances at the "Revenue vs EPS" chart to verify growth trends.
    - **Success**: User determines if the stock is worth further research in < 1 minute.

2.  **Valuation Modeling**:
    - User believes "PLTR" will grow revenue at 25% annually.
    - User opens the "Valuation Modeler" and selects the "Bull Case" tab.
    - User adjusts the Revenue Growth slider to 25% and sets the Exit PE to 40x.
    - **Success**: The tool calculates the 5-Year Price Target and CAGR (e.g., "18% CAGR"), helping the user decide if the current price offers a margin of safety.

3.  **Comparative Screening**:
    - User is undecided between "NVDA" and "AMD".
    - User adds both tickers to the "Comparator".
    - User sees a side-by-side comparison of PE, PEG, forward growth estimates, and profit margins.
    - **Success**: User identifies which company offers better value for growth (e.g., "AMD has lower PEG despite lower growth").

## 3. Functional Requirements

### 3.1. Hybrid Data Service
- **Req-1**: The system **must** use a **Hybrid Data Strategy**:
    - **Primary (Fundamentals)**: `yfinance` for all historical/fundamental data.
    - **Optional (Real-time)**: Questrade API for real-time portfolio pricing if credentials exist.
    - **Fallback**: Use `yfinance` delayed quotes if Questrade fails or is not configured.
- **Req-2**: The system **must** retrieve deep fundamental data (Revenue, EPS, Margins, Cash Flow, Insider Ownership) via the Python bridge.
- **Req-3**: The system **must** gracefully handle data gaps (e.g., missing analyst estimates or Piotroski components) by displaying "N/A" or "Best Effort" estimates.

### 3.2. Dashboard & Visualization
- **Req-4**: The Dashboard **must** display a "Stock Search" bar that allows searching by Ticker Symbol.
- **Req-5**: The Dashboard **must** display an "Expert Metrics" panel containing at least:
    - **PEG Ratio** (Current PE / Growth Rate)
    - **Piotroski F-Score** (Show "Insufficient Data" if < 7 of 9 metrics available)
    - **Insider Ownership %**
    - **Rule of 40 Score** (Growth + Margin) *[Note: Show warning "Best for SaaS/Tech" if sector != Technology/Communication]*
- **Req-6**: The system **must** render interactive charts for:
    - **Revenue vs Net Income** (Historical + Forecast)
    - **EPS Growth** (Historical + Forecast)
    - **Free Cash Flow**
    - **Rule of 40 Trend** (Visualizing the score over time)

### 3.3. Valuation Scenario Modeler
- **Req-7**: The tool **must** provide a "Valuation Modeler" with three editable scenarios: **Bear**, **Base**, and **Bull**.
- **Req-8**: The tool **must** validate user inputs within reasonable ranges:
    - **Revenue Growth**: -50% to +200%
    - **Net Margin**: -100% to +100%
    - **Share Change**: -20% to +20%/year
    - **Exit PE**: 1x to 200x
- **Req-9**: The tool **must** automatically calculate the **5-Year Price Target** using the formula:
  > `Target Price = (Revenue * (1 + Growth)^5 * Net Margin * Exit PE) / (Current Shares * (1 + Share Change)^5)`
- **Req-12**: The tool **must** provide **static contextual guidance** for inputs using hardcoded industry averages (e.g., Tech/SaaS: 25-40x, Healthcare: 15-25x, Retail: 10-20x).
- **Req-13**: The tool **must** generate an **"Expert Analysis Summary"** using threshold logic:
    - **Strong Value**: Price < Bear Target
    - **Potential Value**: Bear < Price < Base Target (Show upside % to Base)
    - **Fairly Valued**: Base < Price < Bull Target
    - **Overvalued**: Price > Bull Target
    - **Justification**: Display the **Required CAGR** to justify the current price (e.g., "Current price implies 15% growth vs your 10% assumption").
- **Req-14**: The dashboard **must** display a **"Recently Analyzed"** list (stored locally) to allow quick navigation to previous tickers.

### 3.4. Comparative Screener
- **Req-10**: The tool **must** allow users to select up to 3 tickers for side-by-side comparison.
- **Req-11**: The comparison view **must** highlight the "winner" for specific metrics (e.g., green highlight for lowest PE, highest Growth).

## 4. Technical Constraints
- **Tech Stack**:
    - **Frontend**: React 19+, Vite, Tailwind CSS (Custom "Luxury Dark" theme).
    - **Backend**: Node.js (Express) with TypeScript.
    - **Data Integration**: Node.js backend invokes Python 3.x script via `child_process.spawn()` to fetch heavy data from `yfinance`.
- **Caching Strategy**:
    - **Fundamental Data (`yfinance`)**: Cache for **15 minutes** (reduce API load).
    - **Real-time Quotes (Questrade)**: Cache for **30 seconds** (balance freshness with rate limits).
- **Performance**:
    - Dashboard load time < 2 seconds for cached tickers.
    - Valuation model recalculations must be instantaneous (< 100ms) on client-side input change.
- **Deployment**:
    - Must be runnable locally via a single startup script (`startup.sh`).
    - Must support cross-platform execution (macOS/Linux/Windows).

## 5. Success Criteria
- **User Engagement**: Users spend > 2 minutes interacting with the Valuation Modeler per session (proxy for value).
- **Data Accuracy**: Financial metrics (PE, Price) match public sources (Yahoo Finance/Google Finance) within 1% variance during market hours.
- **Performance**: "Quick Health Check" flow (Search -> Metrics Visible) completes in under 3 seconds on a standard broadband connection.

## 6. Assumptions & Risks
- **Assumption**: `yfinance` remains a reliable free data source.
    - *Risk*: Yahoo Finance API changes or rate limits could break data fetching.
    - *Mitigation*: Architect the backend to easily swap `yfinance` for an API like FMP (Financial Modeling Prep) if needed.
- **Assumption**: User provides Questrade credentials via `.env` file for real-time data.
    - *Risk*: Questrade rate limits (1 req/sec).
    - *Mitigation*: Implement request throttling and caching in the backend bridge.
