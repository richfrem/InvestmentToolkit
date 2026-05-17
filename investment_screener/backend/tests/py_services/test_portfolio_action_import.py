"""
Tests that portfolio_action.py works when invoked via its py_services/ symlink path.
This is the exact path bridge.ts uses via spawnPythonScript().
A broken sys.path.insert (missing .resolve()) silently returns {} in production.
"""

import subprocess
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = REPO_ROOT / "investment_screener/backend/tests/fixtures"
SYMLINK_PATH = REPO_ROOT / "investment_screener/backend/py_services/portfolio_action.py"
CANONICAL_PATH = REPO_ROOT / "plugins/portfolio-advisor/scripts/portfolio_action.py"


def _run(script_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "python3", str(script_path),
            "--all",
            "--portfolio", str(FIXTURES_DIR / "portfolio.test.json"),
            "--target",   str(FIXTURES_DIR / "target_portfolio.test.json"),
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def test_portfolio_action_via_symlink_path():
    """py_services/ symlink path must work — this is how bridge.ts calls it."""
    r = _run(SYMLINK_PATH)
    assert r.returncode == 0, f"Non-zero exit via symlink: {r.stderr}"
    data = json.loads(r.stdout)
    assert len(data) > 0, "Expected non-empty action map via symlink path"


def test_portfolio_action_via_canonical_path():
    """Canonical plugin path must also work."""
    r = _run(CANONICAL_PATH)
    assert r.returncode == 0, f"Non-zero exit via canonical path: {r.stderr}"
    data = json.loads(r.stdout)
    assert len(data) > 0, "Expected non-empty action map via canonical path"
