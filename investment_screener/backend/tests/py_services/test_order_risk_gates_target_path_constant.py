import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402


def test_target_portfolio_path_constant_includes_theses_subdirectory():
    """The real file lives at data/theses/target-portfolio.json (confirmed by
    compute_conviction_scores.py's TARGET_PATH and apply_catalyst.py's THESIS_JSON
    constants). order_risk_gates.py's TARGET_PORTFOLIO_PATH default was found stale
    (missing the theses/ subdirectory) during Wave 2 investigation -- currently masked
    because every call site overrides it, but a latent landmine for any future caller
    that doesn't. This test locks in the correct value so it can't silently regress.
    """
    assert "theses" in str(order_risk_gates.TARGET_PORTFOLIO_PATH)
    assert str(order_risk_gates.TARGET_PORTFOLIO_PATH).endswith(
        "theses/target-portfolio.json"
    )
