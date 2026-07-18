"""Tests for consolidate_research.py database consolidator."""
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from consolidate_research import run_consolidation  # noqa: E402


def test_consolidate_research(tmp_path):
    # Set up temp folder layout
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    projections_dir = tmp_path / "projections"
    projections_dir.mkdir()
    
    # Create mock projection
    proj_content = """[
        {
            "ticker": "PLTR",
            "savedAt": "2026-07-02T14:43:58.000Z",
            "aiThesis": {
                "fairValue": 147.06,
                "action": "HOLD"
            }
        }
    ]"""
    (projections_dir / "PLTR.json").write_text(proj_content)
    
    # Create dated research md files
    (research_dir / "PLTR_2026-05-02.md").write_text("# PLTR Deep Dive (2026-05-02)\n\nOld content")
    (research_dir / "PLTR_2026-07-02.md").write_text("# PLTR Deep Dive (2026-07-02)\n\nNew content")
    
    # Run consolidator
    run_consolidation(
        research_dir=str(research_dir),
        projections_dir=str(projections_dir),
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
