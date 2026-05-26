import json
import subprocess
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "investment_screener" / "backend" / "py_services" / "lock_and_normalize_targets.py"

def test_lock_and_normalize_missing_required_args():
    """Test that running the script without args fails and prints help/error."""
    r = subprocess.run(
        ["python3", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    # At this point, the file doesn't exist, so this will fail with python3: can't open file ...
    # This is a perfect failing test because the script doesn't exist yet!
    assert r.returncode != 0

def test_lock_and_normalize_happy_path(tmp_path):
    """Test locking and normalizing targets using a temporary target-portfolio.json file."""
    dummy_portfolio = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 40.0, "role": "core"},
            {"ticker": "MSFT", "targetWeight": 30.0, "role": "core"},
            {"ticker": "GOOG", "targetWeight": 20.0, "role": "core"},
            {"ticker": "INTC", "targetWeight": 10.0, "role": "core"}
        ]
    }
    target_file = tmp_path / "target-portfolio.json"
    target_file.write_text(json.dumps(dummy_portfolio))

    # Run script to set INTC=0, lock GOOG=25.0, adjust MSFT=15.0, and normalize AAPL
    # Sum of locked + adjusts = GOOG(25.0) + MSFT(15.0) = 40.0
    # Remaining for AAPL = 60.0%
    r = subprocess.run(
        [
            "python3", str(SCRIPT_PATH),
            "--target-file", str(target_file),
            "--zeros", "INTC",
            "--locks", "GOOG=25.0",
            "--adjusts", "MSFT=15.0",
            "--write"
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

    assert r.returncode == 0, f"Script failed: {r.stdout}\n{r.stderr}"
    
    # Reload and verify
    with open(target_file) as f:
        data = json.load(f)
    
    holdings_dict = {h["ticker"]: h["targetWeight"] for h in data["holdings"]}
    
    assert holdings_dict["INTC"] == 0.0
    assert holdings_dict["GOOG"] == 25.0
    assert holdings_dict["MSFT"] == 15.0
    assert holdings_dict["AAPL"] == 60.0
    assert round(sum(holdings_dict.values()), 4) == 100.0
