# Feature Specification: Screener UI Improvements

## 1. Overview
### Goal
Improve the Investment Screener's usability, layout efficiency, and data accuracy across the Valuation, Analysis, and Dashboard views. This spec addresses layout density, broken Yahoo Finance data integration, chart flexibility, analyst forecast visualization, and navigation functionality.

### Scope
This spec covers UI/UX improvements to the existing `tools/investment-screener/` application. It does **not** introduce new backend services or external API integrations beyond what Yahoo Finance (`yfinance`) already provides.

> **Note**: This is an incremental spec. Additional issues may be appended in future revisions.

## 2. Issues

### Issue 1: Compact Valuation Layout
**Problem**: The Valuation tab requires too much vertical scrolling to see all sliders and scenario results.
**Solution**: Adopt a denser, more compact slider arrangement:
- Reduce vertical spacing between slider groups.
- Consider tighter grouping (e.g., 3 sliders per row where screen width allows).
- Ensure Bear/Base/Bull scenario cards and sliders are visible with minimal scrolling on a standard 1080p display.

### Issue 2: Fix Yahoo API Reference Values
**Problem**: All Yahoo reference values on the Valuation Modeler sliders display "Yahoo: N/A%" (Growth Rate, Net Margin, Exit P/E, Share Change). The "Reset to Yahoo" button has no valid data to reset to.
**Solution**:
- Debug the Python `yfinance` bridge to identify why fundamental data (analyst growth estimates, margin data, forward P/E) is not being returned or parsed correctly.
- Ensure the backend `/api/stock/:ticker` endpoint returns these fields populated.
- Frontend should display actual Yahoo values below each slider and enable "Reset to Yahoo" functionality.
- If a specific metric is genuinely unavailable for a ticker, display "N/A" with a tooltip explaining why (e.g., "No analyst estimates available").

### Issue 3: Multi-Mode Analysis Chart
**Problem**: The Analysis tab currently shows a fixed set of charts (Rule of 40 Trend + Fundamentals). Users want flexibility to view different financial data trends.
**Solution**:
- Replace the current fixed chart layout with a **single primary chart area** with **toggle buttons** to switch between views:
  - **Revenue & Earnings** (default) — topline revenue + earnings trend over time
  - **Free Cash Flow**
  - **Margins** (Gross, Operating, Net)
  - **EPS Growth**
- Each button swaps the chart data without page navigation.
- Maintain the "Luxury Dark" styling and Recharts library.

### Issue 4: Analyst Forecast Overlay
**Problem**: No visibility into forward-looking analyst consensus estimates on the revenue/earnings chart.
**Solution**:
- On the Revenue & Earnings chart view (Issue 3), extend the timeline with **analyst forecast data** from Yahoo Finance:
  - **2026** (current year) and **2027** (next year) projections.
  - **Three dotted forecast lines**: High estimate, Low estimate, and Average consensus.
- Visual distinction: historical data as solid lines, forecast data as dotted/dashed lines.
- Label the forecast region clearly (e.g., shaded background or "Forecast" annotation).
- Data source: `yfinance` analyst earnings/revenue estimates.

### Issue 5: Rule of 40 as Separate Page
**Problem**: Rule of 40 is currently embedded in the Analysis tab alongside other charts, cluttering the view.
**Solution**:
- Move the Rule of 40 chart and related metrics into its **own dedicated tab** in the top navigation bar (alongside Overview, Analysis, Valuation).
- The Analysis tab then focuses purely on financial data charts (Issue 3).
- The Rule of 40 tab should retain the existing chart and add contextual information (e.g., what Rule of 40 means, the SaaS/Tech warning from the original spec).

### Issue 6: Valuation Layout — Better Use of Screen Real Estate
**Problem**: The Valuation Modeler wastes horizontal space; sliders and scenario results are stacked vertically when they could be arranged more efficiently.
**Solution**:
- Redesign the Valuation Modeler layout to use a **side-by-side arrangement**:
  - **Left panel**: Input sliders (Growth Rate, Net Margin, Exit P/E, Share Change, Discount Rate, Time Horizon).
  - **Right panel**: Scenario results (Bear/Base/Bull targets, CAGR, Expert Analysis Summary).
- Alternatively, use a **top-bottom split**: compact slider row at top, results and chart visualization below.
- The goal is to see inputs and outputs simultaneously without scrolling.

### Issue 7: View/Edit Saved Projections & Notes
**Problem**: The "Save Projection" button exists, but there is no visible way to view, edit, or manage previously saved projections and notes.
**Solution**:
- Add a **"My Projections"** button (or icon) near the "Save Projection" button.
- Clicking it opens a panel/modal listing saved projections for the current ticker:
  - Date saved
  - Scenario values (growth rate, margin, PE, etc.)
  - User notes
- Each entry should have **Edit** and **Delete** actions.
- Allow loading a saved projection back into the sliders for comparison or adjustment.
- Storage: LocalStorage (consistent with existing persistence strategy).

### Issue 8: Functional Dashboard & Settings Links
**Problem**: The sidebar links "Dashboard" and "Settings" in the bottom-left are non-functional placeholders.
**Solution**:
- **Dashboard link**: Navigate to a dashboard/home view (could be the default Overview tab, or a dedicated landing page showing recently analyzed tickers and quick stats).
- **Settings link**: Navigate to a settings page with at minimum:
  - Theme preferences (if applicable)
  - Data cache settings
  - Questrade API configuration status
  - Clear saved data option
- Both links must be wired up with proper routing.

## 3. Technical Constraints
- **Frontend**: React 19+, Vite, Tailwind CSS (existing "Luxury Dark" theme).
- **Charts**: Recharts (existing library).
- **Backend**: Node.js/Express + Python `yfinance` bridge (existing architecture).
- **Storage**: LocalStorage for saved projections and user preferences.
- **Performance**: Chart view switching must be instantaneous (< 100ms). No additional API calls when toggling between chart modes if data is already fetched.

## 4. Success Criteria
- All Yahoo reference values populate correctly for major tickers (AAPL, NVDA, MSFT, INTC, etc.).
- Valuation tab is fully usable without scrolling on a 1080p display.
- Users can switch between 4+ chart views with toggle buttons.
- Analyst forecast lines render correctly with visual distinction from historical data.
- Saved projections can be viewed, edited, and loaded back into the modeler.
- All sidebar navigation links are functional.

## 5. Future Additions
This spec is intentionally incremental. Additional UI improvements will be appended as they are identified.