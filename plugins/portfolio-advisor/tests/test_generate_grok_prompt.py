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
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402

import generate_grok_prompt  # noqa: E402


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
