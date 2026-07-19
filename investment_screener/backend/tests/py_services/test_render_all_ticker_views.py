"""Tests for render_all_ticker_views.py — one-time backfill of generated
research views (.summary.md / .timeline.md) for every ticker already
covered by ACTIVE RESEARCH_IMPORT events in the ledger.

This closes the gap discovered in post-migration validation: the historical
research corpus migration appended events to the ledger but never ran
view_generator, so aiThesis.researchReport pointers (rewritten to
{TICKER}.summary.md) pointed at files that were never created.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.event_store import append_event  # noqa: E402
from render_all_ticker_views import render_all_views  # noqa: E402


def test_render_all_views_writes_files_for_every_ledger_ticker(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "research"

    append_event(
        str(jsonl_path), event_type="RESEARCH_IMPORT", effective_at="2026-07-18",
        status="ACTIVE", title="PLTR research", body_markdown="Palantir body.",
        ticker="PLTR",
    )
    append_event(
        str(jsonl_path), event_type="RESEARCH_IMPORT", effective_at="2026-07-18",
        status="ACTIVE", title="NVDA research", body_markdown="Nvidia body.",
        ticker="NVDA",
    )

    result = render_all_views(str(jsonl_path), str(db_path), str(output_dir))

    assert result["rendered_tickers"] == ["NVDA", "PLTR"]
    assert result["count"] == 2
    assert "Palantir body." in (output_dir / "PLTR.summary.md").read_text()
    assert "Nvidia body." in (output_dir / "NVDA.summary.md").read_text()
    assert (output_dir / "PLTR.timeline.md").exists()
    assert (output_dir / "NVDA.timeline.md").exists()


def test_render_all_views_creates_output_dir_if_missing(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "nested" / "research"

    append_event(
        str(jsonl_path), event_type="RESEARCH_IMPORT", effective_at="2026-07-18",
        status="ACTIVE", title="CORZ research", body_markdown="Core Scientific body.",
        ticker="CORZ",
    )

    result = render_all_views(str(jsonl_path), str(db_path), str(output_dir))

    assert result["count"] == 1
    assert (output_dir / "CORZ.summary.md").exists()


def test_render_all_views_is_idempotent_and_skips_unrelated_event_types(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "research"

    append_event(
        str(jsonl_path), event_type="RESEARCH_IMPORT", effective_at="2026-07-18",
        status="ACTIVE", title="PLTR research", body_markdown="Palantir body.",
        ticker="PLTR",
    )
    append_event(
        str(jsonl_path), event_type="TECHNICAL_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="PLTR technical sweep", body_markdown="Not research.",
        ticker="PLTR",
    )

    first = render_all_views(str(jsonl_path), str(db_path), str(output_dir))
    second = render_all_views(str(jsonl_path), str(db_path), str(output_dir))

    assert first["rendered_tickers"] == ["PLTR"]
    assert second["rendered_tickers"] == ["PLTR"]
    assert "Not research." not in (output_dir / "PLTR.summary.md").read_text()
