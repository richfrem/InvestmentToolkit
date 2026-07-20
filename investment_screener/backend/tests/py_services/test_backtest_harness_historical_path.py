import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import backtest_harness  # noqa: E402


def test_extract_historical_targets_tries_both_pre_and_post_move_paths():
    """extract_historical_targets() reads target-portfolio.json out of historical git
    blobs. The file moved from data/target-portfolio.json to data/theses/
    target-portfolio.json partway through this repo's history (Wave 2 investigation
    finding). A commit-SHA-agnostic historical reader must try both paths, since it
    has no way to know a priori whether a given historical commit predates the move.
    Silently trying only one path means every commit on the other side of the move
    returns empty/wrong data with no error -- the exact failure mode this test guards.
    """
    candidate_paths = backtest_harness.candidate_target_portfolio_paths()
    assert "investment_screener/backend/data/target-portfolio.json" in candidate_paths
    assert (
        "investment_screener/backend/data/theses/target-portfolio.json"
        in candidate_paths
    )
