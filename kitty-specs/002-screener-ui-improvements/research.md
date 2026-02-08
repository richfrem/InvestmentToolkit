# Research Findings: Yahoo Finance Data Integration

## Decision
We will extend the existing `fetch_financials.py` script to fetch additional data points required for the new features, rather than switching to a different provider.

## Rationale
- **Existing Infrastructure**: The project already uses `yfinance`, so extending it minimizes dependencies.
- **Data Availability**: Preliminary checks confirm `yfinance` exposes the necessary data:
    - **Analyst Forecasts**: Available via `stock.revenue_estimate` and `stock.earnings_estimate` DataFrames.
    - **Margins**: Derivable from `stock.financials` (Gross Profit, Operating Income, Net Income) divided by Total Revenue.
    - **Free Cash Flow**: Available in `stock.cashflow` (often under "Free Cash Flow" or calculated as Operating Cash Flow - CapEx).

## Implementation Details

### Data Mapping Strategy

| Metric | Source (`yfinance` object) | Key / Calculation |
| :--- | :--- | :--- |
| **Revenue Forecast** | `stock.revenue_estimate` | Rows `0` (Current Year) and `+1` (Next Year); Cols `avg`, `low`, `high` |
| **Earnings Forecast** | `stock.earnings_estimate` | Rows `0` (Current Year) and `+1` (Next Year); Cols `avg`, `low`, `high` |
| **Free Cash Flow** | `stock.cashflow` | `Free Cash Flow` (if present) OR `Operating Cash Flow` - `Capital Expenditure` |
| **Gross Margin** | `stock.financials` | `Gross Profit` / `Total Revenue` |
| **Operating Margin** | `stock.financials` | `Operating Income` / `Total Revenue` |
| **Net Margin** | `stock.financials` | `Net Income` / `Total Revenue` |
| **EPS History** | `stock.financials` | `Basic EPS` or `Diluted EPS` |

### Fallback Logic
If specific keys are missing (common in `yfinance` as API changes), we will:
1.  Try alternative keys (e.g., `totalCashFromOperatingActivities` vs `Operating Cash Flow`).
2.  Return `null` or `0` for that specific metric rather than failing the whole request.
3.  Frontend will render "N/A" for missing data points.

## Alternatives Considered
- **Financial Modeling Prep (FMP) API**: Better structured data but requires an API key and potentially a paid subscription for forecast data. Rejected to keep the project "local first" and free.
- **Alpha Vantage**: Rate limits are too strict for a smooth UI experience.
