#!/usr/bin/env python3
"""
Unit test for portfolio_inspect.py CLI tool.
"""
import subprocess
import sys
from pathlib import Path

def test_portfolio_inspect_cli_single_symbol():
    # File is at: investment_screener/backend/tests/py_services/test_portfolio_inspect.py
    # .parent = py_services
    # .parent.parent = tests
    # .parent.parent.parent = backend
    # .parent.parent.parent.parent = investment_screener
    # .parent.parent.parent.parent.parent = workspace_root
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    script = repo_root / "investment_screener" / "backend" / "py_services" / "portfolio_inspect.py"
    
    res = subprocess.run(
        [sys.executable, str(script), "--symbol", "IREN", "--json"],
        capture_output=True,
        text=True,
        cwd=str(repo_root)
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}"
    assert "IREN" in res.stdout
    assert "target_weight" in res.stdout
    assert "shares" in res.stdout

if __name__ == "__main__":
    test_portfolio_inspect_cli_single_symbol()
    print("test_portfolio_inspect_cli_single_symbol PASSED")
