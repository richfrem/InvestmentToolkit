"""Tests for consolidate_research.py database consolidator.

Wave 1 Task 7B rewired `load_latest_projection` off `projections/{TICKER}.json`
onto `domain_model.sqlite` (ADR-029) — this test now seeds a `tmp_path`-backed
SQLite database via `initialize_db` instead of writing a projections directory,
never touching the real `data/domain_model.sqlite` file.
"""
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402

from consolidate_research import run_consolidation  # noqa: E402


def test_consolidate_research(tmp_path):
    # Set up temp folder layout
    research_dir = tmp_path / "research"
    research_dir.mkdir()

    # Seed a projection_version row in a tmp_path SQLite DB
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "PLTR", asset_class="EQUITY", name="Palantir")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-02T14:43:58.000Z",
            fair_value=147.06, action="HOLD",
        )
    finally:
        conn.close()

    # Create dated research md files
    (research_dir / "PLTR_2026-05-02.md").write_text("# PLTR Deep Dive (2026-05-02)\n\nOld content")
    (research_dir / "PLTR_2026-07-02.md").write_text("# PLTR Deep Dive (2026-07-02)\n\nNew content")

    # Run consolidator
    run_consolidation(
        research_dir=str(research_dir),
        db_path=str(db_path),
        delete_old=True
    )

    # Check results
    consolidated_file = research_dir / "PLTR.md"
    assert consolidated_file.exists()

    text = consolidated_file.read_text()
    assert "ticker: PLTR" in text
    assert "fairValue: 147.06" in text
    assert "Old content" in text
    assert "New content" in text

    # Check deletion
    assert not (research_dir / "PLTR_2026-05-02.md").exists()
    assert not (research_dir / "PLTR_2026-07-02.md").exists()


def test_load_latest_projection_returns_empty_for_unknown_ticker(tmp_path):
    from consolidate_research import load_latest_projection

    db_path = tmp_path / "test.sqlite"
    initialize_db(str(db_path)).close()

    assert load_latest_projection("ZZZZ", str(db_path)) == {}


def test_load_latest_projection_picks_newest_by_saved_at_regardless_of_source(tmp_path):
    """Original code sorted ALL entries (any source) by savedAt desc — no
    AI_AGENT filter. A newer ETF_ANALYSIS row must win over an older AI_AGENT one."""
    from consolidate_research import load_latest_projection

    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=40.0, action="HOLD", source="AI_AGENT",
        )
        save_projection_version(
            conn, investment_id, version=2, saved_at="2026-07-01T00:00:00Z",
            fair_value=45.0, action="INITIATE", source="ETF_ANALYSIS",
        )
    finally:
        conn.close()

    proj = load_latest_projection("DXYZ", str(db_path))
    assert proj["aiThesis"]["fairValue"] == 45.0
    assert proj["aiThesis"]["action"] == "INITIATE"
