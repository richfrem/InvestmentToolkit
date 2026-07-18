import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.view_generator import render_ticker_views  # noqa: E402


def test_render_ticker_views_writes_summary_and_timeline(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("""
        INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
        VALUES ('evt_1', 1, 'us-pltr', 'RESEARCH_IMPORT', '2026-07-18', '2026-07-18', 'ACTIVE', 'PLTR research import', 'Palantir ontology builds secure node.', 'hash_1');
    """)
    conn.commit()

    output_dir = tmp_path / "research"
    output_dir.mkdir()
    render_ticker_views("PLTR", conn, str(output_dir))

    summary = (output_dir / "PLTR.summary.md").read_text()
    timeline = (output_dir / "PLTR.timeline.md").read_text()
    assert "ticker: \"PLTR\"" in summary
    assert "documentType: generated-research-summary" in summary
    assert "Palantir ontology builds secure node." in timeline
