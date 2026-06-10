import subprocess
import json
from pathlib import Path

# Paths to script
REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "investment_screener" / "backend" / "py_services" / "verify_thesis_sync.py"

def run_sync_checker(thesis_json: Path, thesis_md: Path, projections_dir: Path) -> subprocess.CompletedProcess:
    """Helper to execute verify_thesis_sync.py with customized paths via subprocess."""
    return subprocess.run(
        [
            "python3", str(SCRIPT_PATH),
            "--thesis-json", str(thesis_json),
            "--thesis-md", str(thesis_md),
            "--projections-dir", str(projections_dir)
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

def test_verify_thesis_sync_perfect_alignment(tmp_path):
    """Test that perfect alignment between json, markdown, and projections passes successfully."""
    # 1. Create target-portfolio.json
    portfolio_data = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 40.0, "role": "core"},
            {"ticker": "MSFT", "targetWeight": 60.0, "role": "core"}
        ]
    }
    thesis_json = tmp_path / "target-portfolio.json"
    thesis_json.write_text(json.dumps(portfolio_data))

    # 2. Create investment_thesis.md mentioning both tickers
    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("Conviction Pillars:\n- AAPL is leading mobile ecosystem.\n- MSFT dominates cloud software.")

    # 3. Create projection files for AAPL and MSFT
    proj_dir = tmp_path / "projections"
    proj_dir.mkdir()
    (proj_dir / "AAPL.json").write_text("{}")
    (proj_dir / "MSFT.json").write_text("{}")

    # Run check
    r = run_sync_checker(thesis_json, thesis_md, proj_dir)
    assert r.returncode == 0, f"Sync check failed but was expected to pass: {r.stdout}\n{r.stderr}"
    assert "All Synchronization Checks Passed successfully!" in r.stdout

def test_verify_thesis_sync_fail_weights(tmp_path):
    """Test that target weights summing to != 100% causes validation failure."""
    portfolio_data = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 40.0, "role": "core"},
            {"ticker": "MSFT", "targetWeight": 55.0, "role": "core"}  # Sums to 95%
        ]
    }
    thesis_json = tmp_path / "target-portfolio.json"
    thesis_json.write_text(json.dumps(portfolio_data))

    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("- AAPL\n- MSFT")

    proj_dir = tmp_path / "projections"
    proj_dir.mkdir()
    (proj_dir / "AAPL.json").write_text("{}")
    (proj_dir / "MSFT.json").write_text("{}")

    # Run check
    r = run_sync_checker(thesis_json, thesis_md, proj_dir)
    assert r.returncode == 1
    assert "Total target weight sums to 95.0000% (must be 100% ± 0.1%)" in r.stdout
    assert "Sync Verification FAILED" in r.stdout

def test_verify_thesis_sync_fail_missing_md_mention(tmp_path):
    """Test that a ticker in target portfolio missing from thesis md causes failure."""
    portfolio_data = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 40.0, "role": "core"},
            {"ticker": "TSLA", "targetWeight": 60.0, "role": "core"}
        ]
    }
    thesis_json = tmp_path / "target-portfolio.json"
    thesis_json.write_text(json.dumps(portfolio_data))

    # AAPL is mentioned but TSLA is missing
    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("Conviction Pillars:\n- AAPL is leading mobile ecosystem.")

    proj_dir = tmp_path / "projections"
    proj_dir.mkdir()
    (proj_dir / "AAPL.json").write_text("{}")
    (proj_dir / "TSLA.json").write_text("{}")

    # Run check
    r = run_sync_checker(thesis_json, thesis_md, proj_dir)
    assert r.returncode == 1
    assert "The following tickers exist in target portfolio but are missing in thesis documentation: ['TSLA']" in r.stdout
    assert "Sync Verification FAILED" in r.stdout

def test_verify_thesis_sync_fail_missing_projection(tmp_path):
    """Test that active business holding missing a projection JSON causes failure."""
    portfolio_data = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 40.0, "role": "core"},
            {"ticker": "MSFT", "targetWeight": 60.0, "role": "core"}
        ]
    }
    thesis_json = tmp_path / "target-portfolio.json"
    thesis_json.write_text(json.dumps(portfolio_data))

    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("- AAPL\n- MSFT")

    proj_dir = tmp_path / "projections"
    proj_dir.mkdir()
    (proj_dir / "AAPL.json").write_text("{}")
    # MSFT.json is missing

    # Run check
    r = run_sync_checker(thesis_json, thesis_md, proj_dir)
    assert r.returncode == 1
    assert "are missing DCF projections" in r.stdout
    assert "['MSFT']" in r.stdout
    assert "Sync Verification FAILED" in r.stdout

def test_verify_thesis_sync_spot_and_cash_exemption(tmp_path):
    """Test that spot ETFs and cash holdings are exempt from the projection checks."""
    portfolio_data = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 50.0, "role": "core"},
            {"ticker": "IBIT", "targetWeight": 30.0, "role": "speculative"}, # Spot Bitcoin ETF
            {"ticker": "CAD", "targetWeight": 20.0, "role": "reserve", "subStrategyId": "cash"} # Cash reserve
        ]
    }
    thesis_json = tmp_path / "target-portfolio.json"
    thesis_json.write_text(json.dumps(portfolio_data))

    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("Thesis:\n- AAPL is core tech.\n- IBIT for digital gold.\n- CAD for dry powder.")

    proj_dir = tmp_path / "projections"
    proj_dir.mkdir()
    (proj_dir / "AAPL.json").write_text("{}")
    # No IBIT.json or CAD.json created, they are spot/cash and exempt!

    # Run check
    r = run_sync_checker(thesis_json, thesis_md, proj_dir)
    assert r.returncode == 0, f"Sync check failed: {r.stdout}\n{r.stderr}"
    assert "Found 1 active equity/business thesis holdings requiring DCF projections." in r.stdout
    assert "All Synchronization Checks Passed successfully!" in r.stdout
