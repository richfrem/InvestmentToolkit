"""
test_repo_root.py — one way for plugin scripts to find the repository root.

Fixed-depth Path(__file__).parents[3] only works from plugins/<plugin>/scripts/.
From an installed skill copy (.agents/skills/<skill>/scripts/) it lands on
.agents/, so the installed /daily verifier found no runs and the runner would
have written receipts to .agents/context/control_plane.db (2026-09-29).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from repo_root import RepoRootNotFound, find_repo_root  # noqa: E402


def _fake_repo(tmp_path: Path) -> Path:
    root = tmp_path / "InvestmentToolkit"
    (root / "investment_screener").mkdir(parents=True)
    return root


@pytest.mark.parametrize("script_dir", [
    "plugins/portfolio-advisor/scripts",           # canonical plugin script
    "plugins/portfolio-advisor/skills/daily-loop/scripts",  # skill spoke (symlink path)
    ".agents/skills/daily-loop/scripts",            # installed hard copy
])
def test_finds_the_repo_root_from_every_script_location(tmp_path, script_dir):
    root = _fake_repo(tmp_path)
    script = root / script_dir / "run_daily.py"
    script.parent.mkdir(parents=True)
    script.write_text("")
    assert find_repo_root(script) == root


def test_fails_loudly_outside_a_repo(tmp_path):
    lonely = tmp_path / "somewhere" / "scripts" / "run_daily.py"
    lonely.parent.mkdir(parents=True)
    lonely.write_text("")
    with pytest.raises(RepoRootNotFound):
        find_repo_root(lonely)


def test_this_checkout_resolves_to_the_real_repo():
    here = Path(__file__).resolve()
    assert (find_repo_root(here) / "investment_screener").is_dir()
