"""Tests for research_parity_report.py: it reports ledger parity for on-disk research and writes nothing."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from intelligence.db_client import initialize_db as initialize_ledger  # noqa: E402
from domain_model.db_client import initialize_db as initialize_domain  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
import research_parity_report as rpr  # noqa: E402


def _add_event(conn, seq, key, body="", event_id=None, content_hash=None, event_type="RESEARCH_IMPORT"):
    conn.execute(
        "INSERT INTO intelligence_event (event_id, event_sequence, event_type, effective_at, ingested_at, "
        "status, title, body_markdown, idempotency_key, content_hash) "
        "VALUES (?, ?, ?, '2026-10-01', '2026-10-01T00:00:00Z', 'ACTIVE', 't', ?, ?, ?)",
        (event_id or f"evt_{seq}", seq, event_type, body, key, content_hash or f"hash{seq}"),
    )


def _data_dir(tmp_path):
    conn = initialize_ledger(str(tmp_path / "intelligence.sqlite"))
    _add_event(conn, 1, "research-import-AAA_2026-10-01.md", body="same text")
    _add_event(conn, 2, "research-import-BBB_2026-10-01.md", body="older text")
    _add_event(conn, 3, "daily-brief-2026-10-01", event_type="REVIEW_DAILY")
    conn.commit()
    conn.close()
    research = tmp_path / "research"
    (research / "archive").mkdir(parents=True)
    (research / "AAA_2026-10-01.md").write_text("same text")
    (research / "BBB_2026-10-01.md").write_text("newer text")
    (research / "CCC_2026-10-01.md").write_text("never imported")
    (research / "archive" / "DDD_2026-05-02.md").write_text("archived, never imported")
    (research / "AAA.md").write_text("consolidated")
    (research / "AAA.summary.md").write_text("summary")
    return tmp_path


def test_research_files_are_classified_by_key_and_content(tmp_path):
    report = rpr.build_report(_data_dir(tmp_path))
    research = report["research"]
    assert research["present"] == ["AAA_2026-10-01.md"]
    assert research["content_differs"] == ["BBB_2026-10-01.md"]
    assert sorted(research["missing"]) == ["CCC_2026-10-01.md", "archive/DDD_2026-05-02.md"]
    assert sorted(research["derived"]) == ["AAA.md", "AAA.summary.md"]


def test_event_jsonl_lines_match_by_key_id_or_hash(tmp_path):
    data = _data_dir(tmp_path)
    lines = [
        {"event_id": "x1", "idempotency_key": "research-import-AAA_2026-10-01.md"},
        {"event_id": "evt_2"},
        {"event_id": "x3", "content_hash": "hash3"},
        {"event_id": "gone", "event_type": "TECHNICAL_SWEEP", "ticker": "STM", "idempotency_key": "ta-sweep-STM-2026-08-24"},
    ]
    (data / "observations.jsonl").write_text("\n".join(json.dumps(r) for r in lines) + "\n")
    result = rpr.build_report(data)["observations_jsonl"]
    assert result["lines"] == 4 and result["present"] == 3
    assert [m["event_id"] for m in result["missing"]] == ["gone"]


def test_daily_briefs_and_projections(tmp_path):
    data = _data_dir(tmp_path)
    (data / "daily-briefs").mkdir()
    (data / "daily-briefs" / "2026-10-01.json").write_text("{}")
    (data / "daily-briefs" / "2026-10-02.json").write_text("{}")
    (data / "projections").mkdir()
    (data / "projections" / "NVDA.json").write_text("{}")
    (data / "projections" / "AMD.json").write_text("{}")
    conn = initialize_domain(str(data / "domain_model.sqlite"))
    investment_id = resolve_investment(conn, "NVDA")
    conn.execute(
        "INSERT INTO projection_version (projection_id, investment_id, version, saved_at) "
        "VALUES ('p1', ?, 1, '2026-10-01')", (investment_id,),
    )
    conn.commit()
    conn.close()
    report = rpr.build_report(data)
    assert report["daily_briefs"] == {"present": ["2026-10-01.json"], "missing": ["2026-10-02.json"]}
    assert report["projections"] == {"present": ["NVDA.json"], "missing": ["AMD.json"]}


def test_report_writes_nothing_and_tolerates_missing_databases(tmp_path):
    before = sorted(p.name for p in tmp_path.iterdir())
    report = rpr.build_report(tmp_path)
    assert report["ledger_events"] == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == before
