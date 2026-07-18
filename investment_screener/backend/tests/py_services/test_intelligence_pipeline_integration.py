"""True end-to-end integration tests for the intelligence read-model pipeline.

Every other test in this suite exercises a single module in isolation
(``test_replay_ledger.py`` hand-writes JSONL; ``test_view_generator.py``
hand-inserts rows via raw SQL). Nothing drives the full chain from the
sanctioned public API through to a generated file — which is exactly the gap
that let the researchReport-nesting and dropped-column bugs slip past every
task-scoped test. These tests wire the real chain together with no step
mocked or bypassed:

    event_store.append_event   (JSONL ledger — source of truth)
        -> db_client.initialize_db + replay_ledger.replay_events_to_db
        -> view_generator.render_ticker_views
        -> assert generated file content reflects the original event.

Test tier: Category B (file I/O).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.event_store import append_event  # noqa: E402
from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.replay_ledger import replay_events_to_db  # noqa: E402
from intelligence.view_generator import render_ticker_views  # noqa: E402


def test_full_pipeline_append_replay_render(tmp_path):
    """Append -> replay -> render: the generated view must contain the
    original event's title and body, proving the whole chain is wired."""
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "research"
    output_dir.mkdir()

    append_event(
        str(jsonl_path),
        event_type="RESEARCH_IMPORT",
        effective_at="2026-07-18",
        status="ACTIVE",
        title="Palantir Ontology Milestone",
        body_markdown="Palantir ships secure ontology node for defense.",
        ticker="PLTR",
    )

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
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
    replay both, and confirm the generated view surfaces only the ACTIVE
    (superseding) event — the superseded one must not appear."""
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "research"
    output_dir.mkdir()

    original_id = append_event(
        str(jsonl_path),
        event_type="RESEARCH_IMPORT",
        effective_at="2026-07-01",
        status="ACTIVE",
        title="Stale PLTR Research",
        body_markdown="OUTDATED narrative that should be superseded.",
        ticker="PLTR",
    )
    append_event(
        str(jsonl_path),
        event_type="RESEARCH_IMPORT",
        effective_at="2026-07-18",
        status="ACTIVE",
        title="Current PLTR Research",
        body_markdown="CURRENT narrative that supersedes the old one.",
        ticker="PLTR",
        supersedes_event_id=original_id,
    )

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
        render_ticker_views("PLTR", conn, str(output_dir))
    finally:
        conn.close()

    summary = (output_dir / "PLTR.summary.md").read_text()
    timeline = (output_dir / "PLTR.timeline.md").read_text()
    assert "CURRENT narrative that supersedes the old one." in summary
    assert "CURRENT narrative that supersedes the old one." in timeline
    assert "OUTDATED narrative that should be superseded." not in summary
    assert "OUTDATED narrative that should be superseded." not in timeline
