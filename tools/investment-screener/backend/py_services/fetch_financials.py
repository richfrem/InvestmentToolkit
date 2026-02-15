#!/usr/bin/env python3
"""
fetch_financials.py
=====================================

Purpose:
    Fetches comprehensive financial data for a given ticker symbol.
    Provides fundamental metrics, analyst forecasts, historical trends,
    and expert scores (Rule of 40, Piotroski F-Score).

Layer: Tools / Investment-Screener

Usage Examples:
    python tools/investment-screener/backend/py_services/fetch_financials.py MSFT

CLI Arguments:
    ticker_symbol   : The stock ticker to analyze

Key Functions:
    - fetch_expert_metrics()   : Calculates Rule of 40 and Piotroski score.
    - fetch_forecasts()        : Retrieves analyst revenue and earnings estimates.
    - fetch_financial_data()   : Main orchestrator for data retrieval.

Related:
    - fetch_portfolio_heatmap.py
"""

import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

import yfinance as yf
import pandas as pd
import numpy as np


class NpEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling Numpy types."""
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


def get_metric(info_dict: Dict[str, Any], key: str, default: Any = 0) -> Any:
    """Safely retrieves a metric from the info dictionary."""
    val = info_dict.get(key)
    return val if val is not None else default


def fetch_forecasts(stock: yf.Ticker, current_year: int) -> tuple:
    """
    Extracts analyst revenue and earnings forecasts.

    Returns:
        tuple: (revenue_forecasts, earnings_forecasts)
    """
    rev_forecast = []
    earn_forecast = []

    try:
        # Revenue Estimates
        rev_est = stock.revenue_estimate
        if rev_est is not None and not rev_est.empty:
            for period, year_offset in [('0y', 0), ('+1y', 1)]:
                if period in rev_est.index:
                    row = rev_est.loc[period]
                    rev_forecast.append({
                        "year": current_year + year_offset,
                        "avg": row.get('avg', 0),
                        "low": row.get('low', 0),
                        "high": row.get('high', 0),
                        "period": period
                    })

        # Earnings Estimates
        earn_est = stock.earnings_estimate
        if earn_est is not None and not earn_est.empty:
            for period, year_offset in [('0y', 0), ('+1y', 1)]:
                if period in earn_est.index:
                    row = earn_est.loc[period]
                    earn_forecast.append({
                        "year": current_year + year_offset,
                        "avg": row.get('avg', 0),
                        "low": row.get('low', 0),
                        "high": row.get('high', 0),
                        "period": period
                    })
    except Exception as e:
        print(f"Forecast fetch failed: {e}", file=sys.stderr)

    return rev_forecast, earn_forecast


def fetch_performance_metrics(stock: yf.Ticker, current_year: int) -> Dict[str, float]:
    """Retrieves historical price performance percentages."""
    perf = {
        "1d": 0, "1w": 0, "1m": 0, "3m": 0, "ytd": 0, "1y": 0, "5y": 0
    }
    try:
        hist = stock.history(period="5y")
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]

            def get_change(days_ago_idx):
                if len(hist) > days_ago_idx:
                    prev_price = hist['Close'].iloc[-days_ago_idx]
                    return float(((current_price - prev_price) / prev_price) * 100)
                return 0.0

            perf.update({
                "1d": float(((current_price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100)) if len(hist) > 1 else 0.0,
                "1w": get_change(5),
                "1m": get_change(21),
                "3m": get_change(63),
                "1y": get_change(252),
                "5y": get_change(len(hist) - 1)
            })

            # YTD Calculation
            start_of_year = f"{current_year}-01-01"
            ytd_data = hist.loc[hist.index >= start_of_year]
            if not ytd_data.empty:
                start_price = ytd_data['Close'].iloc[0]
                perf["ytd"] = float(((current_price - start_price) / start_price) * 100)
    except Exception as e:
        print(f"Error fetching performance metrics: {e}", file=sys.stderr)

    return perf


def calculate_piotroski_score(financials: pd.DataFrame, balance_sheet: pd.DataFrame, 
                              cashflow: pd.DataFrame, info: Dict[str, Any], indices: dict) -> Dict[str, Any]:
    """
    Calculates the 9-point Piotroski F-Score for financial health.

    Args:
        financials: Income statement.
        balance_sheet: Balance sheet.
        cashflow: Cash flow statement.
        info: Ticker info dict.
        indices: Dictionary containing 'latest' and 'prev' column indices.

    Returns:
        Dictionary with total score and breakdown details.
    """
    l_idx = indices['latest']
    p_idx = indices['prev']
    score = 0
    details = {}

    def get_val(df, keys, idx):
        if df.empty: return 0
        if isinstance(keys, str): keys = [keys]
        for k in keys:
            if k in df.index:
                val = df.loc[k].iloc[idx]
                return float(val) if not pd.isna(val) else 0
        return 0

    # 1. Profitability (4 points)
    net_inc = get_val(financials, ['Net Income', 'NetIncome'], l_idx)
    prev_net_inc = get_val(financials, ['Net Income', 'NetIncome'], p_idx)
    op_cash = get_val(cashflow, ['Operating Cash Flow', 'Total Cash From Operating Activities'], l_idx)
    total_assets = get_val(balance_sheet, ['Total Assets', 'TotalAssets'], l_idx)
    prev_assets = get_val(balance_sheet, ['Total Assets', 'TotalAssets'], p_idx)
    avg_assets = (total_assets + prev_assets) / 2 if (total_assets and prev_assets) else total_assets
    roa = net_inc / avg_assets if avg_assets else 0
    prev_roa = prev_net_inc / prev_assets if prev_assets else 0

    details['roa_positive'] = roa > 0
    details['cfo_positive'] = op_cash > 0
    details['roa_improving'] = roa > prev_roa
    details['accruals_ok'] = op_cash > net_inc
    score += sum([details['roa_positive'], details['cfo_positive'], details['roa_improving'], details['accruals_ok']])

    # 2. Leverage/Liquidity (3 points)
    debt = get_val(balance_sheet, ['Long Term Debt', 'LongTermDebt'], l_idx)
    prev_debt = get_val(balance_sheet, ['Long Term Debt', 'LongTermDebt'], p_idx)
    lev = debt / avg_assets if avg_assets else 0
    prev_lev = prev_debt / prev_assets if prev_assets else 0
    
    curr_ass = get_val(balance_sheet, 'Current Assets', l_idx)
    curr_liab = get_val(balance_sheet, 'Current Liabilities', l_idx)
    prev_curr_ass = get_val(balance_sheet, 'Current Assets', p_idx)
    prev_curr_liab = get_val(balance_sheet, 'Current Liabilities', p_idx)
    curr_ratio = curr_ass / curr_liab if curr_liab else 0
    prev_curr_ratio = prev_curr_ass / prev_curr_liab if prev_curr_liab else 0

    shares = get_metric(info, 'sharesOutstanding', 0)
    prev_shares = get_val(balance_sheet, ['Share Issued', 'Ordinary Shares Number'], p_idx)
    
    details['leverage_decreasing'] = lev < prev_lev
    details['current_ratio_improving'] = curr_ratio > prev_curr_ratio
    details['no_dilution'] = (shares <= prev_shares) if (shares and prev_shares) else True
    score += sum([details['leverage_decreasing'], details['current_ratio_improving'], details['no_dilution']])

    # 3. Operating Efficiency (2 points)
    rev = get_val(financials, ['Total Revenue', 'Revenue'], l_idx)
    prev_rev = get_val(financials, ['Total Revenue', 'Revenue'], p_idx)
    gp = get_val(financials, 'Gross Profit', l_idx)
    prev_gp = get_val(financials, 'Gross Profit', p_idx)
    gm = (gp / rev) if rev else 0
    prev_gm = (prev_gp / prev_rev) if prev_rev else 0
    
    asset_turnover = rev / avg_assets if avg_assets else 0
    prev_asset_turnover = prev_rev / prev_assets if prev_assets else 0

    details['gross_margin_improving'] = gm > prev_gm
    details['asset_turnover_improving'] = asset_turnover > prev_asset_turnover
    score += sum([details['gross_margin_improving'], details['asset_turnover_improving']])

    return {"score": score, "max": 9, "details": details}


def fetch_financial_data(ticker_symbol: str) -> None:
    """
    Main orchestration function for fetching and printing financial data.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        current_year = datetime.now().year

        # 1. Basic Metrics
        rev_growth = get_metric(info, 'revenueGrowth')
        profit_margin = get_metric(info, 'profitMargins')
        forward_pe = get_metric(info, 'forwardPE', get_metric(info, 'trailingPE'))

        # 2. Forecasts & Performance
        res_rev_f, res_earn_f = fetch_forecasts(stock, current_year)
        perf = fetch_performance_metrics(stock, current_year)

        # 2b. Analyst & Growth Estimates (ADR 018)
        analyst_est = {
            "target_high_price": info.get('targetHighPrice', 0),
            "target_low_price": info.get('targetLowPrice', 0),
            "target_mean_price": info.get('targetMeanPrice', 0),
            "target_median_price": info.get('targetMedianPrice', 0),
            "recommendation": info.get('recommendationKey', 'N/A'),
            "number_of_analysts": info.get('numberOfAnalystOpinions', 0)
        }

        # 2c. Calculate Revenue Growth Estimate (Fix for VRT 200% outlier)
        # Previously used earnings_trend (EPS growth), which caused massive overestimation for DCF revenue models.
        # Now deriving from Analyst Revenue Forecasts: (+1y Avg - 0y Avg) / 0y Avg
        
        growth_est = {"stockTrend": {"+1y": 0}}
        calculated_growth = 0.0
        
        rev_0y = next((x['avg'] for x in res_rev_f if x['period'] == '0y'), 0)
        rev_1y = next((x['avg'] for x in res_rev_f if x['period'] == '+1y'), 0)
        
        if rev_0y and rev_1y and rev_0y > 0:
            calculated_growth = ((rev_1y - rev_0y) / rev_0y) * 100
        elif rev_0y and rev_0y > 0:
            # Fallback: 0y vs TTM
            ttm_rev = info.get('totalRevenue', hist_rev[-1] if hist_rev else 0)
            if ttm_rev > 0:
                calculated_growth = ((rev_0y - ttm_rev) / ttm_rev) * 100
        
        if calculated_growth != 0:
             growth_est["stockTrend"]["+1y"] = round(calculated_growth, 2)
        else:
             # Fallback to info 'revenueGrowth' (Quarterly YoY) if no forecasts
             growth_est["stockTrend"]["+1y"] = round(info.get('revenueGrowth', 0) * 100, 2)

        # 3. Financial Statements
        financials = stock.financials.reindex(sorted(stock.financials.columns), axis=1)
        balance_sheet = stock.balance_sheet.reindex(sorted(stock.balance_sheet.columns), axis=1)
        cashflow = stock.cashflow.reindex(sorted(stock.cashflow.columns), axis=1)

        years_count = len(financials.columns)
        if years_count == 0:
            print(json.dumps({"error": "Insufficient historical data"}))
            return

        # Indices for newest vs previous available year
        idx = {'latest': years_count - 1, 'prev': max(0, years_count - 2)}

        # 4. Historical Trends (ADR 018)
        def get_series(df, keys):
            if df.empty: return []
            if isinstance(keys, str): keys = [keys]
            for k in keys:
                if k in df.index:
                    return [float(v) if not pd.isna(v) else 0 for v in df.loc[k]]
            return []

        hist_rev = get_series(financials, ['Total Revenue', 'Revenue'])
        hist_ni = get_series(financials, ['Net Income', 'NetIncome'])
        hist_fcf = get_series(cashflow, ['Free Cash Flow', 'FreeCashFlow'])
        hist_eps = get_series(financials, ['Basic EPS', 'BasicEPS'])

        # Calculate Margins
        hist_gp = get_series(financials, 'Gross Profit')
        hist_ebitda = get_series(financials, 'EBITDA')
        hist_op_inc = get_series(financials, ['Operating Income', 'OperatingIncome'])

        hist_gm = [gp/rev if rev and rev != 0 else 0 for gp, rev in zip(hist_gp, hist_rev)]
        hist_om = [op/rev if rev and rev != 0 else 0 for op, rev in zip(hist_op_inc, hist_rev)]
        hist_nm = [ni/rev if rev and rev != 0 else 0 for ni, rev in zip(hist_ni, hist_rev)]

        # 5. Expert Calculations
        piotroski = calculate_piotroski_score(financials, balance_sheet, cashflow, info, idx)
        
        # Rule of 40
        latest_rev = hist_rev[-1] if hist_rev else 0
        ebitda = hist_ebitda[-1] if hist_ebitda else 0
        ebitda_margin = (ebitda / latest_rev) if latest_rev != 0 else 0
        rule_of_40 = round((rev_growth * 100) + (ebitda_margin * 100), 2)

        # 5. Result Construction
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
                "pe_ratio": info.get('trailingPE', 0),
                "forward_pe": forward_pe,
                "market_cap": info.get('marketCap', 0),
                "shares_outstanding": info.get('sharesOutstanding', 0),
                "beta": info.get('beta', 0),
                "revenue": info.get('totalRevenue', hist_rev[-1] if hist_rev else 0),
                "peg_ratio": info.get('pegRatio'),
                "revenue_growth": round(rev_growth * 100, 2),
                "profit_margin": round(profit_margin * 100, 2)
            },
            "performance": perf,
            "expert_metrics": {
                "rule_of_40": {
                    "score": rule_of_40, 
                    "revenue_growth": round(rev_growth * 100, 2),
                    "ebitda_margin": round(ebitda_margin * 100, 2),
                    "is_saas": info.get('sector') == 'Technology'
                },
                "piotroski_f_score": piotroski
            },
            "financials": {
                "historical_revenue": hist_rev,
                "historical_net_income": hist_ni,
                "historical_fcf": hist_fcf,
                "historical_gross_margin": hist_gm,
                "historical_operating_margin": hist_om,
                "historical_net_margin": hist_nm,
                "historical_eps": hist_eps
            },
            "analyst_estimates": analyst_est,
            "growth_estimates": growth_est,
            "analyst_revenue_forecast": res_rev_f,
            "analyst_earnings_forecast": res_earn_f
        }

        print(json.dumps(result, indent=2, cls=NpEncoder))

    except Exception as e:
        print(json.dumps({"error": str(e)}))


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker provided"}))
        sys.exit(1)
        
    ticker = sys.argv[1]
    fetch_financial_data(ticker)


if __name__ == "__main__":
    main()
