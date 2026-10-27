"""Tests for generate_news_prompt.py's Wave 1 Task 7B rewire of `load_dcf` onto
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

import generate_news_prompt  # noqa: E402


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

    assert generate_news_prompt.load_dcf("ZZZZ", db_path=db_path) == {}


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

    assert generate_news_prompt.load_dcf("DXYZ", db_path=db_path) == {}


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

    dcf = generate_news_prompt.load_dcf("NVDA", db_path=db_path)
    assert dcf["action"] == "ACCUMULATE"
    assert dcf["fairValue"] == 200.0
    assert dcf["price"] == 150.0
    assert dcf["upside"] == round((200.0 - 150.0) / 150.0 * 100, 1)
    assert dcf["savedAt"] == "2026-07-01"


def test_build_prompt_reads_target_weight_from_sqlite_not_json_file(tmp_path, monkeypatch):
    """build_prompt() takes pillarId, role, agentRationale and targetWeight per
    holding from domain_model.sqlite."""
    db_path = tmp_path / "test.sqlite"
    _seed_thesis_holding(db_path)
    monkeypatch.setattr(generate_news_prompt, "DB_PATH", db_path)

    prompt = generate_news_prompt.build_prompt("2026-07-25")

    assert "NVDA" in prompt


def test_has_no_file_thesis_source():
    src = (REPO_ROOT / "plugins/portfolio-advisor/scripts/generate_news_prompt.py").read_text()
    assert "THESIS_JSON" not in src
    assert "compute_target" not in src


def test_sa_lp_section_reflects_the_july_2026_liquidation(tmp_path, monkeypatch):
    """2026-10-01: the prompt told every model that SA LP's Q4 2025 positions
    "reinforce the portfolio". Situational Awareness LP was forced to sell its public
    holdings to Citadel on 2026-07-30 (CNBC, TechCrunch), so ChatGPT and Gemini treated
    stale 6/30 13F data as a live, reinforcing signal while Grok and Opus got it right.
    The prompt must not present the old position list as current sponsorship and must
    tell the model the fund's public book was liquidated.
    """
    db_path = tmp_path / "test.sqlite"
    _seed_thesis_holding(db_path)
    monkeypatch.setattr(generate_news_prompt, "DB_PATH", db_path)

    prompt = generate_news_prompt.build_prompt("2026-10-01")

    sa_section = prompt.split("## SA LP Cross-Check", 1)[1].split("## Output Format", 1)[0]
    assert "Q4 2025 top positions" not in sa_section
    assert "2026-07-30" in sa_section
    assert "liquidat" in sa_section.lower()
    assert "do not treat" in sa_section.lower()
