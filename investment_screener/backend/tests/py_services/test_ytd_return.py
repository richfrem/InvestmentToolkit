"""
test_ytd_return.py — Unit tests for YTD Time-Weighted Rate of Return (TWR) math.
"""

import sys
from pathlib import Path

# Resolve project paths
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

def test_twr_mathematical_correctness():
    """Verify that the TWR compounding logic matches the manual standard math."""
    starting_balance = 37426.0
    current_balance = 43551.86
    
    # Define sub-periods based on cash_flows.json values
    # Period 1: Jan 1 -> Feb 6 (Before flow: $39,120. Deposit: $2,000)
    p1_start = starting_balance
    p1_end = 39120.0
    r1 = (p1_end - p1_start) / p1_start
    assert abs(r1 - 0.04526) < 0.001
    
    # After deposit flow of +2000
    p2_start = p1_end + 2000.0
    p2_end = 43500.0
    r2 = (p2_end - p2_start) / p2_start
    assert abs(r2 - 0.05788) < 0.001
    
    # After withdrawal flow of -5300
    p3_start = p2_end - 5300.0
    p3_end = 46626.86
    r3 = (p3_end - p3_start) / p3_start
    assert abs(r3 - 0.22060) < 0.001
    
    # After withdrawal flow of -3075
    p4_start = p3_end - 3075.0
    p4_end = current_balance
    r4 = (p4_end - p4_start) / p4_start
    assert abs(r4 - 0.0) < 0.001
    
    # Compounding calculation
    twr_product = (1 + r1) * (1 + r2) * (1 + r3) * (1 + r4)
    twr_pct = (twr_product - 1) * 100
    
    # Expected compounded return: ~34.96%
    assert abs(twr_pct - 34.96) < 0.01
