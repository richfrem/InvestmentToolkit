#!/usr/bin/env python3
"""
fetch_financials.py - Fetches detailed financial data for a stock using yfinance.

Optimized with local filesystem caching (1 hour) to prevent rate limiting.
"""

import sys
import json
import os
import time
import hashlib
import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# --- Caching Configuration ---
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_DURATION = 3600  # 1 hour in seconds

# --- Custom Encoder for Numpy Types (Global) ---
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

# --- Caching Functions ---
def get_cached_data(ticker):
    """Retrieve cached data if valid."""
    if not os.path.exists(CACHE_DIR):
        return None
    
    # Simple sanitization for filename
    safe_ticker = "".join([c for c in ticker if c.isalnum() or c in ('-','.')])
    cache_file = os.path.join(CACHE_DIR, f"{safe_ticker}.json")
    
    if not os.path.exists(cache_file):
        return None
        
    try:
        # Check expiration
        if time.time() - os.path.getmtime(cache_file) > CACHE_DURATION:
            return None
            
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def save_to_cache(ticker, data):
    """Save data to cache."""
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        safe_ticker = "".join([c for c in ticker if c.isalnum() or c in ('-','.')])
        cache_file = os.path.join(CACHE_DIR, f"{safe_ticker}.json")
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, cls=NpEncoder)
    except Exception as e:
        # Silently fail on cache write errors to avoid breaking the main output flow
        pass

def fetch_financial_data(ticker_symbol):
    # 1. Try Cache First
    cached = get_cached_data(ticker_symbol)
    if cached:
        print(json.dumps(cached, indent=2))
        return

    try:
        stock = yf.Ticker(ticker_symbol)
        
        # --- Helper for Metrics ---
        def get_metric(info_dict, key, default=0):
            val = info_dict.get(key)
            if val is None: return default
            return val

        # 2. Fetch Basic Info
        info = stock.info
        
        revenue_growth = get_metric(info, 'revenueGrowth')
        profit_margin = get_metric(info, 'profitMargins')
        forward_pe = get_metric(info, 'forwardPE')
        trailing_pe = get_metric(info, 'trailingPE')
        if forward_pe == 0 and trailing_pe != 0:
            forward_pe = trailing_pe

        # --- Analyst Forecast Extraction ---
        analyst_revenue_forecast = []
        analyst_earnings_forecast = []
        
        try:
            current_year = datetime.datetime.now().year
            
            # Revenue Estimates
            rev_est = stock.revenue_estimate
            if rev_est is not None and not rev_est.empty:
                for i, period, year_offset in [(0, '0y', 0), (1, '+1y', 1)]:
                    if period in rev_est.index:
                        row = rev_est.loc[period]
                        analyst_revenue_forecast.append({
                            "year": current_year + year_offset,
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
            print(json.dumps({"warning": f"Forecast fetch failed: {str(e)}", "partial": True}), file=sys.stderr)

        # --- Growth Estimates Extraction ---
        growth_estimates = None
        try:
            ge = stock.growth_estimates
            if ge is not None and not ge.empty:
                stock_trend = {}
                if 'stockTrend' in ge.columns:
                    for period in ['0q', '+1q', '0y', '+1y']:
                        if period in ge.index:
                            val = ge.loc[period, 'stockTrend']
                            if pd.notna(val):
                                stock_trend[period] = float(val)
                    
                    if stock_trend:
                        growth_estimates = {"stockTrend": stock_trend}
        except Exception as e:
            print(f"Growth estimates fetch failed: {e}", file=sys.stderr)

        # --- Performance Metrics ---
        performance = {}
        try:
            hist = stock.history(period="5y")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                
                def get_change(days_ago_idx):
                    if len(hist) > days_ago_idx:
                        prev_price = hist['Close'].iloc[-days_ago_idx]
                        return float(((current_price - prev_price) / prev_price) * 100)
                    return 0.0

                performance = {
                    "1d": float(((current_price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100)) if len(hist) > 1 else 0.0,
                    "1w": get_change(5),
                    "1m": get_change(21),
                    "3m": get_change(63),
                    "ytd": 0.0,
                    "1y": get_change(252),
                    "5y": get_change(len(hist) - 1)
                }
                
                # YTD Calculation
                start_of_year = f"{current_year}-01-01"
                ytd_data = hist.loc[hist.index >= start_of_year]
                if not ytd_data.empty:
                     start_price = ytd_data['Close'].iloc[0]
                     performance["ytd"] = float(((current_price - start_price) / start_price) * 100)
        except Exception as e:
            print(f"Error fetching history: {e}", file=sys.stderr)


        # --- Financial Statements ---
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        if financials.empty:
             print(json.dumps({"error": "Insufficient financial data"}), file=sys.stderr)
             pass 

        # SORT FINANCIALS BY DATE (Oldest -> Newest)
        financials = financials.reindex(sorted(financials.columns), axis=1)
        if not balance_sheet.empty:
            balance_sheet = balance_sheet.reindex(sorted(balance_sheet.columns), axis=1)
        if not cashflow.empty:
            cashflow = cashflow.reindex(sorted(cashflow.columns), axis=1)

        # Helper to safely get value for a year index (0 = oldest after sort)
        def get_value(df, key_aliases, index):
            try:
                if isinstance(key_aliases, str):
                    key_aliases = [key_aliases]
                
                for key in key_aliases:
                    if key in df.index:
                        val = df.loc[key].iloc[index]
                        return float(val) if not pd.isna(val) else 0
                return 0
            except (KeyError, IndexError):
                return 0

        # Extract last 5 years (or fewer if not available)
        years_count = min(5, len(financials.columns))
        
        # Historical Lists (ordered Oldest -> Newest)
        hist_revenue = [get_value(financials, ['Total Revenue', 'Revenue', 'TotalRevenue'], i) for i in range(years_count)]
        hist_net_income = [get_value(financials, ['Net Income', 'NetIncome'], i) for i in range(years_count)]
        hist_eps = [get_value(financials, ['Basic EPS', 'EPS', 'BasicEPS'], i) for i in range(years_count)]
        
        # Margins Logic
        gross_profit = [get_value(financials, ['Gross Profit', 'GrossProfit'], i) for i in range(years_count)]
        operating_income = [get_value(financials, ['Operating Income', 'OperatingIncome', 'EBIT'], i) for i in range(years_count)]
        
        hist_gross_margin = []
        hist_operating_margin = []
        hist_net_margin = []

        for i in range(years_count):
            rev = hist_revenue[i]
            if rev != 0:
                hist_gross_margin.append(float(gross_profit[i] / rev * 100))
                hist_operating_margin.append(float(operating_income[i] / rev * 100))
                hist_net_margin.append(float(hist_net_income[i] / rev * 100))
            else:
                hist_gross_margin.append(0)
                hist_operating_margin.append(0)
                hist_net_margin.append(0)

        # FCF Logic
        hist_fcf = []
        if not cashflow.empty:
             for i in range(years_count):
                ocf = get_value(cashflow, ['Operating Cash Flow', 'Total Cash From Operating Activities'], i)
                capex = get_value(cashflow, ['Capital Expenditure', 'Capital Expenditures'], i)
                # CapEx negative in Yahoo, so Add it to OCF to subtract
                fcf = ocf + capex 
                hist_fcf.append(fcf)
        else:
            hist_fcf = [0] * years_count
            
        # Ensure performance object is populated
        if not performance:
            performance = {
                "1d": 0, "1w": 0, "1m": 0, "3m": 0, "ytd": 0, "1y": 0, "5y": 0
            }

        # --- Rule of 40 & Piotroski Calculations (using latest year) ---
        latest_idx = years_count - 1
        prev_idx = years_count - 2 if years_count > 1 else latest_idx

        # Rule of 40
        current_revenue = hist_revenue[latest_idx]
        previous_revenue = hist_revenue[prev_idx]
        
        calc_rev_growth = 0
        if previous_revenue != 0:
             calc_rev_growth = (current_revenue - previous_revenue) / previous_revenue
        
        final_rev_growth = revenue_growth if revenue_growth != 0 else calc_rev_growth
        
        ubiq_ebitda = get_value(financials, 'EBITDA', latest_idx)
        if ubiq_ebitda == 0: ubiq_ebitda = get_value(financials, 'Operating Income', latest_idx)
        
        ebitda_margin = (ubiq_ebitda / current_revenue) if current_revenue != 0 else 0
        rule_of_40_score = (final_rev_growth * 100) + (ebitda_margin * 100)

        # Piotroski F-Score (Full 9-point methodology)
        piotroski_score = 0
        piotroski_details = {}

        # Data Points (Latest & Previous Year)
        net_inc = hist_net_income[latest_idx]
        prev_net_inc = hist_net_income[prev_idx]
        op_cash = get_value(cashflow, ['Operating Cash Flow', 'Total Cash From Operating Activities'], latest_idx)

        total_assets = get_value(balance_sheet, ['Total Assets', 'TotalAssets'], latest_idx)
        prev_total_assets = get_value(balance_sheet, ['Total Assets', 'TotalAssets'], prev_idx)
        avg_assets = (total_assets + prev_total_assets) / 2 if (total_assets and prev_total_assets) else total_assets

        roa = net_inc / avg_assets if avg_assets else 0
        prev_roa = prev_net_inc / prev_total_assets if prev_total_assets else 0

        # --- Profitability (4 points) ---
        # 1. ROA > 0
        piotroski_details['roa_positive'] = roa > 0
        if roa > 0: piotroski_score += 1

        # 2. Operating Cash Flow > 0
        piotroski_details['cfo_positive'] = op_cash > 0
        if op_cash > 0: piotroski_score += 1

        # 3. ROA improving
        piotroski_details['roa_improving'] = roa > prev_roa
        if roa > prev_roa: piotroski_score += 1

        # 4. Accruals
        piotroski_details['accruals_ok'] = op_cash > net_inc
        if op_cash > net_inc: piotroski_score += 1

        # --- Leverage/Liquidity (3 points) ---
        # 5. Leverage decreasing
        long_term_debt = get_value(balance_sheet, ['Long Term Debt', 'LongTermDebt'], latest_idx)
        prev_long_term_debt = get_value(balance_sheet, ['Long Term Debt', 'LongTermDebt'], prev_idx)
        leverage = long_term_debt / avg_assets if avg_assets else 0
        prev_leverage = prev_long_term_debt / prev_total_assets if prev_total_assets else 0
        piotroski_details['leverage_decreasing'] = leverage < prev_leverage
        if leverage < prev_leverage: piotroski_score += 1

        # 6. Current ratio improving
        current_assets = get_value(balance_sheet, ['Current Assets', 'CurrentAssets'], latest_idx)
        current_liabilities = get_value(balance_sheet, ['Current Liabilities', 'CurrentLiabilities'], latest_idx)
        prev_current_assets = get_value(balance_sheet, ['Current Assets', 'CurrentAssets'], prev_idx)
        prev_current_liabilities = get_value(balance_sheet, ['Current Liabilities', 'CurrentLiabilities'], prev_idx)
        current_ratio = current_assets / current_liabilities if current_liabilities else 0
        prev_current_ratio = prev_current_assets / prev_current_liabilities if prev_current_liabilities else 0
        piotroski_details['current_ratio_improving'] = current_ratio > prev_current_ratio
        if current_ratio > prev_current_ratio: piotroski_score += 1

        # 7. No new shares issued
        shares = get_metric(info, 'sharesOutstanding', 0)
        prev_shares = get_value(balance_sheet, ['Share Issued', 'CommonStockSharesOutstanding', 'Ordinary Shares Number'], prev_idx)
        no_dilution = shares <= prev_shares if (shares and prev_shares) else True
        piotroski_details['no_dilution'] = no_dilution
        if no_dilution: piotroski_score += 1

        # --- Operating Efficiency (2 points) ---
        # 8. Gross margin improving
        gross_margin_improving = hist_gross_margin[latest_idx] > hist_gross_margin[prev_idx] if years_count > 1 else False
        piotroski_details['gross_margin_improving'] = gross_margin_improving
        if gross_margin_improving: piotroski_score += 1

        # 9. Asset turnover improving
        asset_turnover = current_revenue / avg_assets if avg_assets else 0
        prev_avg_assets = prev_total_assets
        prev_asset_turnover = previous_revenue / prev_avg_assets if prev_avg_assets else 0
        piotroski_details['asset_turnover_improving'] = asset_turnover > prev_asset_turnover
        if asset_turnover > prev_asset_turnover: piotroski_score += 1

        # --- Construct Final Result ---
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
                "shares_outstanding": info.get('sharesOutstanding', 0),
                "revenue_growth": round(final_rev_growth * 100, 2),
                "profit_margin": round(profit_margin * 100, 2)
            },
            "performance": performance,
            "expert_metrics": {
                "rule_of_40": {
                    "score": round(rule_of_40_score, 2),
                    "revenue_growth": round(final_rev_growth * 100, 2),
                    "ebitda_margin": round(ebitda_margin * 100, 2),
                    "is_saas": info.get('sector') == 'Technology'
                },
                "piotroski_f_score": {
                    "score": piotroski_score,
                    "max": 9,
                    "details": piotroski_details
                }
            },
            "financials": {
                 "historical_revenue": hist_revenue,
                 "historical_net_income": hist_net_income,
                 "historical_fcf": hist_fcf,
                 "historical_gross_margin": hist_gross_margin,
                 "historical_operating_margin": hist_operating_margin,
                 "historical_net_margin": hist_net_margin,
                 "historical_eps": hist_eps
            },
            "analyst_revenue_forecast": analyst_revenue_forecast,
            "analyst_earnings_forecast": analyst_earnings_forecast,
            "growth_estimates": growth_estimates,
            "analyst_estimates": {
                "target_high_price": get_metric(info, 'targetHighPrice', 0),
                "target_low_price": get_metric(info, 'targetLowPrice', 0),
                "target_mean_price": get_metric(info, 'targetMeanPrice', 0),
                "target_median_price": get_metric(info, 'targetMedianPrice', 0),
                "recommendation": info.get('recommendationKey', '').replace('_', ' ').title() if info.get('recommendationKey') else '',
                "number_of_analysts": get_metric(info, 'numberOfAnalystOpinions', 0),
                "revenue_growth": round(final_rev_growth * 100, 2),
                "profit_margin": round(profit_margin * 100, 2),
                "forward_pe": forward_pe
            }
        }

        # 3. Save to Cache
        save_to_cache(ticker_symbol, result)

        print(json.dumps(result, indent=2, cls=NpEncoder))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker provided"}))
        sys.exit(1)
        
    ticker = sys.argv[1]
    fetch_financial_data(ticker)
