import json
import math
import sys
import os

def calculate_scenario_price(s, snapshot, time_horizon, discount_rate):
    """
    Replicates the exact DCF logic from ValuationModeler.tsx:
    1. Future Revenue = Current Revenue * (1 + g)^t
    2. Future Net Income = Future Revenue * (margin)
    3. Future Market Cap = Future Net Income * PE * Quality
    4. Future Share Count = Current Shares * (1 + share_change)^t
    5. Future Price = Market Cap / Shares
    6. PV = Future Price / (1 + r)^t
    """
    
    # 1. Future Revenue
    current_revenue = snapshot.get('revenue', 0)
    growth_rate = s.get('growthRate', 0) / 100.0
    future_revenue = current_revenue * math.pow(1 + growth_rate, time_horizon)

    # 2. Future Net Income
    net_margin = s.get('netMargin', 0) / 100.0
    future_net_income = future_revenue * net_margin

    # 3. Future Market Cap
    exit_pe = s.get('exitPE', 0)
    quality_mult = s.get('qualityMultiplier', 1.0)
    future_market_cap = future_net_income * exit_pe * quality_mult

    # 4. Future Share Count
    current_shares = snapshot.get('shares', 1)
    share_change = s.get('shareChange', 0) / 100.0
    future_shares = current_shares * math.pow(1 + share_change, time_horizon)

    # 5. Future Price
    future_price = future_market_cap / future_shares if future_shares > 0 else 0

    # 6. Discount to PV
    discount = discount_rate / 100.0
    present_value = future_price / math.pow(1 + discount, time_horizon)
    
    return present_value

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 verify_valuation.py <TICKER>")
        sys.exit(1)
        
    ticker = sys.argv[1]
    path = f"tools/investment-screener/backend/data/projections/{ticker}.json"
    
    if not os.path.exists(path):
        print(f"Error: No projection found at {path}")
        sys.exit(1)
        
    with open(path, 'r') as f:
        data = json.load(f)
        
    if isinstance(data, list):
        if not data:
             print("Error: Empty projection list")
             sys.exit(1)
        latest = data[-1]
    else:
        latest = data

    name = latest.get('name', 'Unknown')
    print(f"\n🔍 Verifying Valuation: {ticker} ({name})")
    print(f"   Saved At: {latest.get('savedAt')}")
    print("-" * 60)
    
    snapshot = latest.get('snapshot', {})
    globals = latest.get('globalSettings', {})
    scenarios = latest.get('scenarios', {})
    
    time_horizon = globals.get('timeHorizon', 5)
    discount_rate = globals.get('discountRate', 10)
    
    current_price = snapshot.get('price', 0)
    print(f"   Current Price:  ${current_price:.2f}")
    print(f"   Discount Rate:  {discount_rate}%")
    print(f"   Time Horizon:   {time_horizon} years")
    print("-" * 60)
    
    # Calculate each scenario
    total_val = 0
    total_weight = 0
    
    for s_name in ['bear', 'base', 'bull']:
        s = scenarios.get(s_name)
        if not s: continue
        
        pv = calculate_scenario_price(s, snapshot, time_horizon, discount_rate)
        weight = s.get('weight', 0)
        
        total_val += pv * weight
        total_weight += weight
        
        upside = ((pv - current_price) / current_price) * 100
        
        print(f"📊 {s_name.upper():<4} ({weight*100:>2.0f}%) | Val: ${pv:>6.2f} | Upside: {upside:>+6.1f}%")
        print(f"     Inputs: G={s.get('growthRate')}%  M={s.get('netMargin')}%  PE={s.get('exitPE')}x  Q={s.get('qualityMultiplier')}x")
        
    print("-" * 60)
    weighted_upside = ((total_val - current_price) / current_price) * 100
    print(f"🎯 WEIGHTED FAIR VALUE: ${total_val:.2f} ({weighted_upside:+.1f}%)")
    
    # Check vs Stored Thesis
    stored_fv = latest.get('aiThesis', {}).get('fairValue', 0)
    diff = abs(total_val - stored_fv)
    if diff > 0.1:
        print(f"⚠️  MISMATCH with stored thesis value: ${stored_fv:.2f} (Diff: ${diff:.2f})")
    else:
        print(f"✅ Matches stored thesis value.")

if __name__ == "__main__":
    main()
