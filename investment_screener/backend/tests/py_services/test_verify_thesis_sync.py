"""Tests for verify_thesis_sync.py, which checks the thesis against domain_model.sqlite only.

Purpose:
    Holdings, weights and projections come from the database (--db); the thesis markdown is
    the only file input. The retired --thesis-json option is gone.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""
import subprocess
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



def run_sync_checker(db_path: Path, thesis_md: Path) -> subprocess.CompletedProcess:
    """Run verify_thesis_sync.py against a temporary database and thesis markdown."""
    return subprocess.run(
        ["python3", str(SCRIPT_PATH), "--db", str(db_path), "--thesis-md", str(thesis_md)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def _make_db(tmp_path: Path, holdings: list[dict]) -> Path:
    """holdings: list of {ticker, target_weight, lifecycle_status, sub_strategy_id,
    has_projection, is_watchlisted}."""
    from domain_model.pillar_repository import resolve_pillar, resolve_sub_strategy
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    resolve_pillar(conn, "p", "Pillar")
    resolve_sub_strategy(conn, "cash", "p", "Cash")
    for h in holdings:
        investment_id = resolve_investment(conn, h["ticker"])
        update_investment_fields(
            conn, investment_id,
            target_weight=h.get("target_weight", 0),
            lifecycle_status=h.get("lifecycle_status", ""),
            is_watchlisted=int(h.get("is_watchlisted", False)),
            **({"pillar_id": "p", "sub_strategy_id": h["sub_strategy_id"]} if h.get("sub_strategy_id") else {}),
        )
        if h.get("has_projection"):
            save_projection_version(
                conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
                fair_value=100.0, action="HOLD", source="AI_AGENT",
                snapshot_json="{}",
            )
    conn.close()
    return db_path


def test_verify_thesis_sync_perfect_alignment(tmp_path):
    """Matching weights, markdown mentions and projections pass."""
    db = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "accumulate", "has_projection": True},
    ])
    md = tmp_path / "investment_thesis.md"
    md.write_text("Conviction Pillars:\n- AAPL is leading mobile ecosystem.\n- MSFT dominates cloud software.")
    r = run_sync_checker(db, md)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert "All Synchronization Checks Passed successfully!" in r.stdout


def test_verify_thesis_sync_fail_weights(tmp_path):
    """Weights summing to 95% fail."""
    db = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 55.0, "lifecycle_status": "accumulate", "has_projection": True},
    ])
    md = tmp_path / "investment_thesis.md"
    md.write_text("- AAPL\n- MSFT")
    r = run_sync_checker(db, md)
    assert r.returncode == 1
    assert "Total target weight sums to 95.0000% (must be 100% ± 0.1%)" in r.stdout
    assert "Sync Verification FAILED" in r.stdout


def test_verify_thesis_sync_fail_missing_md_mention(tmp_path):
    """A holding the thesis markdown never mentions fails."""
    db = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "TSLA", "target_weight": 60.0, "lifecycle_status": "accumulate", "has_projection": True},
    ])
    md = tmp_path / "investment_thesis.md"
    md.write_text("Conviction Pillars:\n- AAPL is leading mobile ecosystem.")
    r = run_sync_checker(db, md)
    assert r.returncode == 1
    assert "missing in thesis documentation: ['TSLA']" in r.stdout


def test_verify_thesis_sync_fail_missing_projection(tmp_path):
    """An active holding with no saved projection fails."""
    db = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "accumulate", "has_projection": False},
    ])
    md = tmp_path / "investment_thesis.md"
    md.write_text("- AAPL\n- MSFT")
    r = run_sync_checker(db, md)
    assert r.returncode == 1
    assert "are missing DCF projections" in r.stdout and "['MSFT']" in r.stdout


def test_verify_thesis_sync_spot_and_cash_exemption(tmp_path):
    """Spot ETFs and cash reserves are exempt from the projection check."""
    db = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 50.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "IBIT", "target_weight": 30.0, "lifecycle_status": "accumulate"},
        {"ticker": "CAD", "target_weight": 20.0, "lifecycle_status": "accumulate", "sub_strategy_id": "cash"},
    ])
    md = tmp_path / "investment_thesis.md"
    md.write_text("Thesis:\n- AAPL is core tech.\n- IBIT for digital gold.\n- CAD for dry powder.")
    r = run_sync_checker(db, md)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert "Found 1 active equity/business thesis holdings requiring DCF projections." in r.stdout


def test_retired_thesis_json_option_is_gone(tmp_path):
    """--thesis-json no longer exists, so a stale caller fails loudly, and the source names no retired file."""
    r = subprocess.run(["python3", str(SCRIPT_PATH), "--thesis-json", "x.json"], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert r.returncode == 2 and "unrecognized arguments" in r.stderr
    assert "target-portfolio.json" not in SCRIPT_PATH.read_text()


def test_verify_thesis_sync_reads_holdings_from_sqlite_by_default(tmp_path):
    """Wave 2 consumer cutover: when --thesis-json/--projections-dir are NOT
    passed, holdings and projection existence are read from domain_model.sqlite
    (the projections/ flat-file directory was archived after Wave 1 and no
    longer exists on disk -- this is the real bug this cutover fixes)."""
    db_path = _make_db(tmp_path, [
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "accumulate", "has_projection": True},
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
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "accumulate", "has_projection": False},
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
        {"ticker": "AAPL", "target_weight": 40.0, "lifecycle_status": "accumulate", "has_projection": True},
        {"ticker": "MSFT", "target_weight": 60.0, "lifecycle_status": "accumulate", "has_projection": True},
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
