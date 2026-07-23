import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))


def _seed_two_events(db_path: Path) -> None:
    from intelligence.db_client import initialize_db
    from intelligence.event_repository import insert_event

    conn = initialize_db(str(db_path))
    for i, (eff_date, regime) in enumerate([("2026-07-22", "BULL"), ("2026-07-23", "CONGESTION")], start=1):
        insert_event(conn, {
            "event_id": f"evt_{i}", "event_sequence": i, "instrument_id": None,
            "event_type": "REVIEW_DAILY", "effective_at": eff_date,
            "observed_at": None, "ingested_at": f"{eff_date}T10:00:00Z",
            "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
            "title": f"Daily Brief for {eff_date}", "body_markdown": "x",
            "payload_json": json.dumps({"date": eff_date, "macro_regime": {"regime": regime}}),
            "supersedes_event_id": None, "idempotency_key": f"daily-brief-{eff_date}",
            "content_hash": f"h{i}",
        })
    conn.commit()
    conn.close()


def test_load_yesterday_returns_second_most_recent_event_via_sql(tmp_path, monkeypatch):
    import daily_brief

    db_path = tmp_path / "intelligence.sqlite"
    _seed_two_events(db_path)
    monkeypatch.setattr(daily_brief, "INTELLIGENCE_DB_PATH", str(db_path))
    monkeypatch.setattr(daily_brief, "date", type("FakeDate", (), {"today": staticmethod(lambda: __import__("datetime").date(2026, 7, 24))}))

    result = daily_brief._load_yesterday()

    # Today is 2026-07-24 (not in the DB); the most recent real prior snapshot is 2026-07-23.
    assert result["date"] == "2026-07-23"
    assert result["macro_regime"]["regime"] == "CONGESTION"


def test_load_yesterday_returns_none_when_no_prior_events(tmp_path, monkeypatch):
    import daily_brief

    db_path = tmp_path / "intelligence.sqlite"
    from intelligence.db_client import initialize_db
    initialize_db(str(db_path)).close()
    monkeypatch.setattr(daily_brief, "INTELLIGENCE_DB_PATH", str(db_path))

    assert daily_brief._load_yesterday() is None
