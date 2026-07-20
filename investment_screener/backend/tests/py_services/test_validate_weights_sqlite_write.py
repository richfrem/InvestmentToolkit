"""
Tests validate_weights.py's Wave 2 Task 9 producer cutover: ``--normalize --write``
must persist rescaled targetWeight values via the domain-model repository
(investment.target_weight) instead of rewriting target-portfolio.json in place.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "plugins/portfolio-advisor/scripts/validate_weights.py"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment, resolve_investment  # noqa: E402


def _make_target_json(tmp_path: Path) -> Path:
    target = tmp_path / "target-portfolio.json"
    target.write_text(json.dumps({
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 30},
            {"ticker": "MSFT", "targetWeight": 30},
        ]
    }))
    return target


def test_normalize_write_persists_to_sqlite_not_json(tmp_path):
    target = _make_target_json(tmp_path)
    db_path = tmp_path / "domain_model.sqlite"
    original_mtime = target.stat().st_mtime_ns

    proc = subprocess.run(
        [
            "python3", str(SCRIPT_PATH),
            "--normalize", "--write",
            "--target", str(target),
            "--db", str(db_path),
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr

    # target-portfolio.json must NOT be touched by the new write path.
    assert target.stat().st_mtime_ns == original_mtime

    conn = initialize_db(str(db_path))
    aapl_id = resolve_investment(conn, "AAPL")
    msft_id = resolve_investment(conn, "MSFT")
    aapl = get_investment(conn, aapl_id)
    msft = get_investment(conn, msft_id)
    conn.close()

    assert aapl["target_weight"] == 50.0
    assert msft["target_weight"] == 50.0


def test_normalize_without_write_does_not_touch_db(tmp_path):
    target = _make_target_json(tmp_path)
    db_path = tmp_path / "domain_model.sqlite"

    proc = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--normalize", "--target", str(target), "--db", str(db_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert not db_path.exists()
