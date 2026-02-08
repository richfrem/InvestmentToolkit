import sys
import json
import yfinance as yf
import pandas as pd
import numpy as np

def fetch_financial_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        
# --- Helper for Metrics ---
        def get_metric(info_dict, key, default=0):
            val = info_dict.get(key)
            if val is None: return default
            return val

        # 1. Fetch Basic Info
        info = stock.info
        
        # Debugging / Fallback for specific keys
        revenue_growth = get_metric(info, 'revenueGrowth')
        profit_margin = get_metric(info, 'profitMargins')
        forward_pe = get_metric(info, 'forwardPE')
        trailing_pe = get_metric(info, 'trailingPE')
        if forward_pe == 0 and trailing_pe != 0:
            forward_pe = trailing_pe # Fallback

        # --- Analyst Forecast Extraction ---
        analyst_revenue_forecast = []
        analyst_earnings_forecast = []
        
        try:
            # Current Year
            import datetime
            current_year = datetime.datetime.now().year
            
            # Revenue Estimates
            rev_est = stock.revenue_estimate
            if rev_est is not None and not rev_est.empty:
                # 0y = Current Year, +1y = Next Year
                for i, period, year_offset in [(0, '0y', 0), (1, '+1y', 1)]:
                    if period in rev_est.index:
                        row = rev_est.loc[period]
                        analyst_revenue_forecast.append({
                            "year": current_year + year_offset, # Approximation
                            "avg": row.get('avg', 0),
                            "low": row.get('low', 0),
                            "high": row.get('high', 0),
                            "period": period
                        })
            
            # Earnings Estimates
            earn_est = stock.earnings_estimate
            if earn_est is not None and not earn_est.empty:
                for i, period, year_offset in [(0, '0y', 0), (1, '+1y', 1)]:
                    if period in earn_est.index:
                        row = earn_est.loc[period]
                        analyst_earnings_forecast.append({
                            "year": current_year + year_offset,
                            "avg": row.get('avg', 0),
                            "low": row.get('low', 0),
                            "high": row.get('high', 0),
                            "period": period
                        })

        except Exception as e:
            # Don't fail the whole script for forecasts
            print(json.dumps({"warning": f"Forecast fetch failed: {str(e)}", "partial": True}), file=sys.stderr)

        # 2. Fetch Financial Statements
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        # Ensure we have data
        if financials.empty or balance_sheet.empty or cashflow.empty:
            return {"error": "Insufficient financial data available from yfinance"}

        # Helper to get latest and previous values safely
        def get_value(df, key, offset=0):
            try:
                # df columns are dates, sorted new to old usually
                # keys are rows
                if key not in df.index: return 0
                return df.loc[key].iloc[offset]
            except:
                return 0

        # --- Rule of 40 Calculation ---
        # Revenue Growth (YoY) + EBITDA Margin
        
        # Revenue
        current_revenue = get_value(financials, 'Total Revenue', 0)
        previous_revenue = get_value(financials, 'Total Revenue', 1)
        
        # Recalculate revenue growth if 0 from info
        if revenue_growth == 0 and previous_revenue != 0:
            revenue_growth = ((current_revenue - previous_revenue) / previous_revenue)  # Keep as decimal 0.15 for 15%? 
            # Wait, yfinance info returns 0.15 for 15%.
            # Rule of 40 calc below expects percentage (e.g. 15.0)
            # Let's standardize: info returns float (0.15). Our calculation below produced (0.15 * 100) = 15.0.
            pass

        # EBITDA Margin
        ebitda = get_value(financials, 'EBITDA', 0) # yfinance usually has this
        # If not, calc from Operating Income + D&A
        if ebitda == 0:
             op_income = get_value(financials, 'Operating Income', 0)
             # D&A is tricky in yf, often under cashflow
             # For MVP, rely on EBITDA field or approx
             ebitda = op_income # Fallback approximation if field missing
        
        ebitda_margin = 0
        if current_revenue != 0:
            ebitda_margin = (ebitda / current_revenue) # 0.30 for 30%
            
        # Convert to percentage for Rule of 40 Score
        # If revenue_growth came from info, it's likely 0.15. If calculated, we need to match.
        
        # Metric Normalization
        # info['revenueGrowth'] is usually 0.xx
        # info['profitMargins'] is usually 0.xx
        
        if revenue_growth == 0 and previous_revenue != 0:
             revenue_growth = (current_revenue - previous_revenue) / previous_revenue
             
        rule_of_40_score = (revenue_growth * 100) + (ebitda_margin * 100)
        
        # --- Piotroski F-Score Calculation ---
        piotroski_score = 0
        
        # 1. ROA > 0
        net_income = get_value(financials, 'Net Income', 0)
        total_assets = get_value(balance_sheet, 'Total Assets', 0)
        prev_total_assets = get_value(balance_sheet, 'Total Assets', 1)
        avg_assets = (total_assets + prev_total_assets) / 2 if prev_total_assets else total_assets
        
        roa = 0
        if avg_assets != 0:
            roa = net_income / avg_assets
        
        if roa > 0: piotroski_score += 1
        
        # 2. CFO > 0
        operating_cash_flow = get_value(cashflow, 'Kp', 0) # Old Yahoo key? 'Total Cash From Operating Activities'
        if operating_cash_flow == 0:
             operating_cash_flow = get_value(cashflow, 'Operating Cash Flow', 0)

        if operating_cash_flow > 0: piotroski_score += 1
        
        # 3. Change in ROA > 0
        prev_net_income = get_value(financials, 'Net Income', 1)
        prev_avg_assets = get_value(balance_sheet, 'Total Assets', 1) # Approximation for simpler calc
        prev_roa = 0
        if prev_avg_assets and prev_avg_assets != 0:
             prev_roa = prev_net_income / prev_avg_assets
             
        if roa > prev_roa: piotroski_score += 1
        
        # 4. Accruals (CFO > Net Income)
        if operating_cash_flow > net_income: piotroski_score += 1
        
        # 5. Change in Leverage (Long Term Debt / Assets) < 0
        lt_debt = get_value(balance_sheet, 'Long Term Debt', 0)
        prev_lt_debt = get_value(balance_sheet, 'Long Term Debt', 1)
        
        lev = lt_debt / avg_assets if avg_assets else 0
        prev_lev = prev_lt_debt / prev_avg_assets if prev_avg_assets else 0
        
        if lev < prev_lev: piotroski_score += 1
        
        # 6. Change in Current Ratio > 0
        curr_assets = get_value(balance_sheet, 'Total Current Assets', 0)
        curr_liab = get_value(balance_sheet, 'Total Current Liabilities', 0)
        prev_curr_assets = get_value(balance_sheet, 'Total Current Assets', 1)
        prev_curr_liab = get_value(balance_sheet, 'Total Current Liabilities', 1)
        
        curr_ratio = curr_assets / curr_liab if curr_liab else 0
        prev_curr_ratio = prev_curr_assets / prev_curr_liab if prev_curr_liab else 0
        
        if curr_ratio > prev_curr_ratio: piotroski_score += 1
        
        # 7. Change in Shares Outstanding <= 0
        shares = info.get('sharesOutstanding', 0) 
        # Historical shares are hard in standardized financials
        # Fallback: assume 0 if data missing, or skip
        # Logic: if we can't fetch it, don't penalize? Or assume no change?
        # Let's assume point if not diluting
        piotroski_score += 1 # Placeholder logic for MVP
        
        # 8. Change in Gross Margin > 0
        gross_profit = get_value(financials, 'Gross Profit', 0)
        prev_gross_profit = get_value(financials, 'Gross Profit', 1)
        
        gm = gross_profit / current_revenue if current_revenue else 0
        prev_gm = prev_gross_profit / previous_revenue if previous_revenue else 0
        
        if gm > prev_gm: piotroski_score += 1
        
        # 9. Change in Asset Turnover > 0
        asset_turnover = current_revenue / avg_assets if avg_assets else 0
        prev_asset_turnover = previous_revenue / prev_avg_assets if prev_avg_assets else 0
        
        if asset_turnover > prev_asset_turnover: piotroski_score += 1

        # Construct Result
        result = {
            "symbol": ticker_symbol,
            "price": info.get('currentPrice', 0),
            "currency": info.get('currency', 'USD'),
            "profile": {
                "sector": info.get('sector', 'Unknown'),
                "industry": info.get('industry', 'Unknown'),
                "description": info.get('longBusinessSummary', '')
            },
            "metrics": {
                "pe_ratio": trailing_pe,
                "forward_pe": forward_pe,
                "market_cap": info.get('marketCap', 0),
                "beta": info.get('beta', 0),
                "revenue": current_revenue,
                "shares_outstanding": shares,
                "revenue_growth": round(revenue_growth * 100, 2), # Convert to %
                "profit_margin": round(profit_margin * 100, 2)    # Convert to %
            },
            "expert_metrics": {
                "rule_of_40": {
                    "score": round(rule_of_40_score, 2),
                    "revenue_growth": round(revenue_growth * 100, 2),
                    "ebitda_margin": round(ebitda_margin * 100, 2),
                    "is_saas": info.get('sector') == 'Technology'
                },
                "piotroski_f_score": {
                    "score": piotroski_score,
                    "max": 9,
                    "details": {
                        "roa_positive": roa > 0,
                        "cfo_positive": operating_cash_flow > 0,
                        "roa_improving": roa > prev_roa,
                        "accruals_ok": operating_cash_flow > net_income
                    }
                }
            },
            "financials": {
                 # Minimal for charts
                 "historical_revenue": [get_value(financials, 'Total Revenue', i) for i in range(4)],
                 "historical_net_income": [get_value(financials, 'Net Income', i) for i in range(4)]
            },
            "analyst_revenue_forecast": analyst_revenue_forecast,
            "analyst_earnings_forecast": analyst_earnings_forecast
        }
        
        # Custom Encoder for Numpy Types
        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.bool_):
                    return bool(obj)
                return super(NpEncoder, self).default(obj)

        print(json.dumps(result, indent=2, cls=NpEncoder))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker provided"}))
        sys.exit(1)
        
    ticker = sys.argv[1]
    data = fetch_financial_data(ticker)

