import subprocess
import json
import sys
from pathlib import Path

# Paths to script
REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "investment_screener" / "backend" / "py_services" / "verify_thesis_sync.py"
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)
from domain_model.projection_repository import save_projection_version  # noqa: E402

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


def _make_db(tmp_path: Path, holdings: list[dict]) -> Path:
    """holdings: list of {ticker, target_weight, lifecycle_status, sub_strategy_id,
    has_projection, is_watchlisted}."""
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    for h in holdings:
        investment_id = resolve_investment(conn, h["ticker"])
        update_investment_fields(
            conn, investment_id,
            target_weight=h.get("target_weight", 0),
            lifecycle_status=h.get("lifecycle_status", ""),
            is_watchlisted=int(h.get("is_watchlisted", False)),
        )
        if h.get("has_projection"):
            save_projection_version(
                conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
                fair_value=100.0, action="HOLD", source="AI_AGENT",
                snapshot_json="{}",
            )
    conn.close()
    return db_path


def test_verify_thesis_sync_reads_holdings_from_sqlite_by_default(tmp_path):
    """Wave 2 consumer cutover: when --thesis-json/--projections-dir are NOT
    passed, holdings and projection existence are read from domain_model.sqlite
    (the projections/ flat-file directory was archived after Wave 1 and no
    longer exists on disk -- this is the real bug this cutover fixes)."""
    db_path = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "core", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "core", "has_projection": True},
    ])

    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("Conviction Pillars:\n- AAPL is leading mobile ecosystem.\n- MSFT dominates cloud software.")

    r = subprocess.run(
        [
            "python3", str(SCRIPT_PATH),
            "--db", str(db_path),
            "--thesis-md", str(thesis_md),
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, f"Sync check failed but expected to pass: {r.stdout}\n{r.stderr}"
    assert "All Synchronization Checks Passed successfully!" in r.stdout


def test_verify_thesis_sync_sqlite_default_flags_missing_projection(tmp_path):
    """A holding present in the investment table but with no projection_version
    row is flagged as missing a DCF projection, sourced from SQLite."""
    db_path = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "core", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "core", "has_projection": False},
    ])

    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("- AAPL\n- MSFT")

    r = subprocess.run(
        [
            "python3", str(SCRIPT_PATH),
            "--db", str(db_path),
            "--thesis-md", str(thesis_md),
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 1
    assert "are missing DCF projections" in r.stdout
    assert "['MSFT']" in r.stdout


def test_verify_thesis_sync_excludes_watchlist_only_tickers(tmp_path):
    """A ticker that is only on the watchlist (is_watchlisted=1, no real
    target_weight/role) must NOT be required to have thesis documentation --
    it was never a target/current holding. Confirmed real-data bug: 19 real
    watchlist tickers (AAPL, ALAB, AMZN, etc.) were being flagged as missing
    thesis docs purely because _load_holdings_from_db() returned every row
    in the investment table with no is_watchlisted filter.
    """
    db_path = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "core", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "core", "has_projection": True},
        {"ticker": "NVDA", "target_weight": 0, "lifecycle_status": "", "has_projection": False, "is_watchlisted": True},
    ])

    thesis_md = tmp_path / "investment_thesis.md"
    thesis_md.write_text("Conviction Pillars:\n- AAPL is leading mobile ecosystem.\n- MSFT dominates cloud software.")

    r = subprocess.run(
        [
            "python3", str(SCRIPT_PATH),
            "--db", str(db_path),
            "--thesis-md", str(thesis_md),
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, f"Sync check failed but expected to pass (NVDA is watchlist-only): {r.stdout}\n{r.stderr}"
    assert "NVDA" not in r.stdout or "missing" not in r.stdout.lower()
    assert "Found 2 holdings in target portfolio." in r.stdout
