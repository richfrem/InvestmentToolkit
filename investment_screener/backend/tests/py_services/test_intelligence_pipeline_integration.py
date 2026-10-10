"""True end-to-end integration tests for the intelligence read-model pipeline.

These tests wire the real chain together with no step mocked or bypassed:

    db_client.initialize_db
        -> event_store.append_event   (ledger database is the source of truth)
        -> view_generator.render_ticker_views
        -> assert generated file content reflects the original event.

Test tier: Category B (database and file I/O).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.event_store import append_event  # noqa: E402
from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.view_generator import render_ticker_views  # noqa: E402


def test_full_pipeline_append_render(tmp_path):
    """Append -> render: the generated view must contain the
    original event's title and body, proving the whole chain is wired."""
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "research"
    output_dir.mkdir()

    conn = initialize_db(str(db_path))
    try:
        append_event(
            conn,
            event_type="RESEARCH_IMPORT",
            effective_at="2026-07-18",
            status="ACTIVE",
            title="Palantir Ontology Milestone",
            body_markdown="Palantir ships secure ontology node for defense.",
            ticker="PLTR",
        )
        render_ticker_views("PLTR", conn, str(output_dir))
    finally:
        conn.close()

    summary = (output_dir / "PLTR.summary.md").read_text()
    timeline = (output_dir / "PLTR.timeline.md").read_text()
    assert "Palantir ships secure ontology node for defense." in summary
    assert "Palantir Ontology Milestone" in timeline
    assert "Palantir ships secure ontology node for defense." in timeline


def test_full_pipeline_supersession_hides_superseded_event(tmp_path):
    """Append an original event, then a superseding event referencing it,
    and confirm the generated view surfaces only the ACTIVE
    (superseding) event — the superseded one must not appear."""
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "research"
    output_dir.mkdir()

    conn = initialize_db(str(db_path))
    try:
        original_id = append_event(
            conn,
            event_type="RESEARCH_IMPORT",
            effective_at="2026-07-01",
            status="ACTIVE",
            title="Stale PLTR Research",
            body_markdown="OUTDATED narrative that should be superseded.",
            ticker="PLTR",
        )
        append_event(
            conn,
            event_type="RESEARCH_IMPORT",
            effective_at="2026-07-18",
            status="ACTIVE",
            title="Current PLTR Research",
            body_markdown="CURRENT narrative that supersedes the old one.",
            ticker="PLTR",
            supersedes_event_id=original_id,
        )
        render_ticker_views("PLTR", conn, str(output_dir))
    finally:
        conn.close()

    summary = (output_dir / "PLTR.summary.md").read_text()
    timeline = (output_dir / "PLTR.timeline.md").read_text()
    assert "CURRENT narrative that supersedes the old one." in summary
    assert "CURRENT narrative that supersedes the old one." in timeline
    assert "OUTDATED narrative that should be superseded." not in summary
    assert "OUTDATED narrative that should be superseded." not in timeline
