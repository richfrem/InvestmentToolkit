"""Tests for generate_grok_prompt.py's Wave 1 Task 7B rewire of `load_dcf` onto
domain_model.sqlite (ADR-029). All tests run against a `tmp_path`-backed SQLite
database via `initialize_db` — never the real `data/domain_model.sqlite` file.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import resolve_pillar  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402

import generate_grok_prompt  # noqa: E402


def _seed_thesis_holding(db_path):
    conn = initialize_db(str(db_path))
    resolve_pillar(conn, "compute", "Compute", target_weight=40.0)
    nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
    update_investment_fields(
        conn, nvda_id,
        target_weight=10.0, pillar_id="compute",
        lifecycle_status="accumulate", agent_rationale="Strong AI demand.",
    )
    conn.close()


def test_load_dcf_returns_empty_for_unknown_ticker(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_db(str(db_path)).close()

    assert generate_grok_prompt.load_dcf("ZZZZ", db_path=db_path) == {}


def test_load_dcf_returns_empty_when_no_ai_agent_row(tmp_path):
    """Original code filtered strictly by source == AI_AGENT with no fallback."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            fair_value=40.0, action="INITIATE", source="ETF_ANALYSIS",
        )
    finally:
        conn.close()

    assert generate_grok_prompt.load_dcf("DXYZ", db_path=db_path) == {}


def test_load_dcf_returns_action_fairvalue_and_upside(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            fair_value=200.0, action="ACCUMULATE", source="AI_AGENT",
            snapshot_json='{"price": 150.0}',
        )
    finally:
        conn.close()

    dcf = generate_grok_prompt.load_dcf("NVDA", db_path=db_path)
    assert dcf["action"] == "ACCUMULATE"
    assert dcf["fairValue"] == 200.0
    assert dcf["price"] == 150.0
    assert dcf["upside"] == round((200.0 - 150.0) / 150.0 * 100, 1)
    assert dcf["savedAt"] == "2026-07-01"


def test_build_prompt_reads_target_weight_from_sqlite_not_json_file(tmp_path, monkeypatch):
    """Wave 8 cutover: build_prompt() previously read the whole thesis
    document (pillarId, role, agentRationale, targetWeight per holding)
    directly from the now-retired target-portfolio.json via
    json.loads(THESIS_JSON.read_text()) and
    validate_weights.compute_target(THESIS_JSON) -- same stale-Target%-column
    bug class as generate_review_json.py before its own Wave 8 fix.
    """
    db_path = tmp_path / "test.sqlite"
    _seed_thesis_holding(db_path)
    monkeypatch.setattr(generate_grok_prompt, "DB_PATH", db_path)

    prompt = generate_grok_prompt.build_prompt("2026-07-25")

    assert "NVDA" in prompt


def test_no_longer_references_target_portfolio_json():
    src = (REPO_ROOT / "plugins/portfolio-advisor/scripts/generate_grok_prompt.py").read_text()
    assert "target-portfolio.json" not in src
    assert "THESIS_JSON" not in src
    assert "compute_target" not in src
