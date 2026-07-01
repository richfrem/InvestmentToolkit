import subprocess
import json
import random
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_python_math(revenue, shares, discount_rate, horizon, scenarios):
    cmd = [
        "python3", os.path.join(PROJECT_ROOT, "investment_screener/backend/py_services/dcf_scenarios.py"),
        "--ticker", "TEST", "--revenue", str(revenue), "--shares", str(shares),
        "--scenarios", "-"
    ]
    # dcf_scenarios.py doesn't currently take discount_rate/horizon via CLI easily in its current 'run' call 
    # but uses defaults (10%, 5yr). We will match those in the test.
    proc = subprocess.run(cmd, input=json.dumps(scenarios), text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stderr)
        raise Exception("Python math failed")
    return json.loads(proc.stdout)

def run_ts_math(revenue, shares, discount_rate, horizon, scenarios):
    cmd = ["npx", "tsx", "math_cli.js"]
    input_data = {
        "revenue": revenue,
        "shares": shares,
        "discountRate": discount_rate,
        "horizon": horizon,
        "scenarios": scenarios
    }
    proc = subprocess.run(cmd, input=json.dumps(input_data), text=True, capture_output=True, cwd=os.path.join(PROJECT_ROOT, "investment_screener/frontend"))
    if proc.returncode != 0:
        print(proc.stderr)
        raise Exception("TS math failed")
    return json.loads(proc.stdout)

def test_math_parity():
    # Test 10 random cases
    for i in range(10):
        rev = random.uniform(100e6, 100e9)
        shares = random.uniform(10e6, 10e9)
        discount_rate = 0.10
        horizon = 5
        
        scenarios = {
            "bear": {"weight": 0.2, "growthRate": random.uniform(-10, 5), "netMargin": random.uniform(1, 10), "exitPE": random.uniform(8, 15), "qualityMultiplier": 0.8, "shareChange": 1.0},
            "base": {"weight": 0.5, "growthRate": random.uniform(5, 15), "netMargin": random.uniform(10, 20), "exitPE": random.uniform(15, 25), "qualityMultiplier": 1.0, "shareChange": 0.0},
            "bull": {"weight": 0.3, "growthRate": random.uniform(15, 30), "netMargin": random.uniform(20, 35), "exitPE": random.uniform(25, 40), "qualityMultiplier": 1.2, "shareChange": -1.0}
        }
        
        py_res = run_python_math(rev, shares, discount_rate, horizon, scenarios)
        ts_res = run_ts_math(rev, shares, discount_rate, horizon, scenarios)
        
        print(f"Case {i}: PY_FV={py_res['weightedFairValue']}, TS_FV={ts_res['weightedFairValue']}")
        for s in ["bear", "base", "bull"]:
            print(f"  {s}: PY_PV={py_res['scenarios'][s]['presentValue']}, TS_PV={ts_res['scenarios'][s]['presentValue']}")
        
        assert abs(py_res['weightedFairValue'] - ts_res['weightedFairValue']) <= 0.05
        
        # Check individual scenario PVs
        for s in ["bear", "base", "bull"]:
            assert abs(py_res['scenarios'][s]['presentValue'] - ts_res['scenarios'][s]['presentValue']) <= 0.02

if __name__ == "__main__":
    test_math_parity()
    print("ALL PARITY TESTS PASSED")
