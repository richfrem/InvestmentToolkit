"""
Tests for generate_review_json.py — Wave 8 cutover to domain_model.sqlite.

Real bug this replaces: generate() read the whole thesis document (pillarId,
role, agentRationale, targetWeight per holding) from the now-retired
target-portfolio.json via validate_weights.compute_target(THESIS_JSON) --
this is exactly what powered the Portfolio Table UI's stale "Target %"
column even after investment.target_weight was updated directly in SQLite.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PY_SERVICES))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import resolve_pillar  # noqa: E402
import generate_review_json  # noqa: E402


def _seed(db_path):
    conn = initialize_db(str(db_path))
    resolve_pillar(conn, "compute", "Compute", target_weight=40.0)
    nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
    update_investment_fields(
        conn, nvda_id,
        target_weight=10.0, pillar_id="compute",
        lifecycle_status="accumulate", agent_rationale="Strong AI demand.",
    )
    conn.close()


def test_generate_uses_investment_target_weight_not_json_file(tmp_path):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path)

    review = generate_review_json.generate("2026-07-25", db_path=db_path)

    all_holdings = review["holdings"] + review["holdingsUnchanged"]
    nvda = next((h for h in all_holdings if h["ticker"] == "NVDA"), None)
    assert nvda is not None
    assert nvda["currentTarget"] == 10.0
    assert nvda["pillarId"] == "compute"
    assert nvda["role"] == "accumulate"
    assert nvda["rationale"] == "Strong AI demand."


def test_generate_pillar_list_sourced_from_strategy_pillar_table(tmp_path):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path)

    review = generate_review_json.generate("2026-07-25", db_path=db_path)

    compute_pillar = next((p for p in review["pillars"] if p["id"] == "compute"), None)
    assert compute_pillar is not None
    assert compute_pillar["currentTarget"] == 40.0


def test_generate_no_longer_imports_or_reads_target_portfolio_json():
    """Source-level regression guard: no THESIS_JSON/target-portfolio.json
    reference anywhere in the module."""
    src = (SCRIPT_DIR / "generate_review_json.py").read_text()
    assert "target-portfolio.json" not in src
    assert "THESIS_JSON" not in src
    assert "compute_target" not in src
