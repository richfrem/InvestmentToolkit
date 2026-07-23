import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_repository import (  # noqa: E402
    insert_event,
    list_active_events_for_ticker,
    search_fts,
    get_latest_event_by_type,
    get_latest_event_by_type_and_ticker,
    list_tickers_with_active_event_type,
    list_active_events_by_type,
)


def test_insert_event_returns_true_when_row_inserted(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    result = insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "T1", "body_markdown": "B1", "content_hash": "h1",
    })
    assert result is True


def test_insert_event_returns_false_when_sequence_duplicate(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    base = {
        "event_sequence": 1, "instrument_id": "us-pltr", "event_type": "NEWS_SWEEP",
        "effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE",
        "title": "T1", "body_markdown": "B1",
    }
    assert insert_event(conn, {**base, "event_id": "evt_1", "content_hash": "h1"}) is True
    assert insert_event(conn, {**base, "event_id": "evt_2", "content_hash": "h2"}) is False


def test_insert_event_persists_all_nullable_columns(tmp_path):
    """insert_event must persist every column append_event writes to the
    JSONL ledger — including payload_json, source_id, confidence_score,
    supersedes_event_id, idempotency_key, and observed_at — not just the
    10-column subset. Round-trip a fully-populated event and assert each
    field survives."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    # A prior event the new one can legitimately reference (FK on supersedes_event_id).
    insert_event(conn, {
        "event_id": "evt_prior", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-01", "ingested_at": "2026-07-01",
        "status": "ACTIVE", "title": "Prior", "body_markdown": "Prior body", "content_hash": "h0",
    })
    full_event = {
        "event_id": "evt_full", "event_sequence": 2, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", "observed_at": "2026-07-17",
        "ingested_at": "2026-07-18", "source_id": "src_abc", "confidence_score": 0.85,
        "status": "ACTIVE", "title": "Full", "body_markdown": "Full body",
        "payload_json": '{"k": "v"}', "supersedes_event_id": "evt_prior",
        "idempotency_key": "idem_123", "content_hash": "hfull",
    }
    assert insert_event(conn, full_event) is True

    cursor = conn.execute(
        "SELECT payload_json, source_id, confidence_score, supersedes_event_id, "
        "idempotency_key, observed_at FROM intelligence_event WHERE event_id = 'evt_full';"
    )
    row = cursor.fetchone()
    assert row == (
        '{"k": "v"}', "src_abc", 0.85, "evt_prior", "idem_123", "2026-07-17",
    )


def test_search_fts_returns_matching_events(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "Nvidia Partnership", "body_markdown": "Palantir and Nvidia.",
        "content_hash": "h1",
    })
    results = search_fts(conn, "Nvidia")
    assert len(results) == 1
    assert results[0]["title"] == "Nvidia Partnership"


def test_list_active_events_for_ticker_filters_status_and_ticker(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("INSERT INTO instrument VALUES ('us-nvda', 'NVDA', 'NASDAQ', 'Nvidia', '2026-07-18', NULL);")
    conn.commit()
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-01", "ingested_at": "2026-07-01",
        "status": "ACTIVE", "title": "Older PLTR event", "body_markdown": "Older body.",
        "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_2", "event_sequence": 2, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-10", "ingested_at": "2026-07-10",
        "status": "ACTIVE", "title": "Newer PLTR event", "body_markdown": "Newer body.",
        "content_hash": "h2",
    })
    insert_event(conn, {
        "event_id": "evt_3", "event_sequence": 3, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-15", "ingested_at": "2026-07-15",
        "status": "SUPERSEDED", "title": "Superseded PLTR event", "body_markdown": "Stale body.",
        "content_hash": "h3",
    })
    insert_event(conn, {
        "event_id": "evt_4", "event_sequence": 4, "instrument_id": "us-nvda",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-12", "ingested_at": "2026-07-12",
        "status": "ACTIVE", "title": "NVDA event", "body_markdown": "Other ticker body.",
        "content_hash": "h4",
    })

    results = list_active_events_for_ticker(conn, "PLTR")

    assert [r["event_id"] for r in results] == ["evt_2", "evt_1"]
    assert all(r["status"] == "ACTIVE" for r in results)


def test_get_latest_event_by_type(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    # Insert two REVIEW_DAILY events
    insert_event(conn, {
        "event_id": "evt_old", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-10", "ingested_at": "2026-07-10",
        "status": "ACTIVE", "title": "Old Brief", "body_markdown": "Old", "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_new", "event_sequence": 2, "instrument_id": "us-pltr",
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "New Brief", "body_markdown": "New", "content_hash": "h2",
    })
    insert_event(conn, {
        "event_id": "evt_draft", "event_sequence": 3, "instrument_id": "us-pltr",
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-20", "ingested_at": "2026-07-20",
        "status": "DRAFT", "title": "Draft Brief", "body_markdown": "Draft", "content_hash": "h3",
    })

    result = get_latest_event_by_type(conn, "REVIEW_DAILY")
    assert result is not None
    assert result["event_id"] == "evt_new"


def test_get_latest_event_by_type_and_ticker(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("INSERT INTO instrument VALUES ('us-nvda', 'NVDA', 'NASDAQ', 'Nvidia', '2026-07-18', NULL);")
    conn.commit()
    # Insert TECHNICAL_SWEEP events
    insert_event(conn, {
        "event_id": "evt_pltr_old", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "TECHNICAL_SWEEP", "effective_at": "2026-07-10", "ingested_at": "2026-07-10",
        "status": "ACTIVE", "title": "PLTR Old", "body_markdown": "PLTR Old", "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_pltr_new", "event_sequence": 2, "instrument_id": "us-pltr",
        "event_type": "TECHNICAL_SWEEP", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "PLTR New", "body_markdown": "PLTR New", "content_hash": "h2",
    })
    insert_event(conn, {
        "event_id": "evt_nvda", "event_sequence": 3, "instrument_id": "us-nvda",
        "event_type": "TECHNICAL_SWEEP", "effective_at": "2026-07-19", "ingested_at": "2026-07-19",
        "status": "ACTIVE", "title": "NVDA New", "body_markdown": "NVDA New", "content_hash": "h3",
    })

    result = get_latest_event_by_type_and_ticker(conn, "TECHNICAL_SWEEP", "PLTR")
    assert result is not None
    assert result["event_id"] == "evt_pltr_new"


def test_list_active_events_by_type_returns_all_matching_ordered_desc(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-17",
        "observed_at": None, "ingested_at": "2026-07-17T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-17", "body_markdown": "x",
        "payload_json": '{"date": "2026-07-17"}', "supersedes_event_id": None,
        "idempotency_key": "daily-brief-2026-07-17", "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_2", "event_sequence": 2, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-18",
        "observed_at": None, "ingested_at": "2026-07-18T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-18", "body_markdown": "x",
        "payload_json": '{"date": "2026-07-18"}', "supersedes_event_id": None,
        "idempotency_key": "daily-brief-2026-07-18", "content_hash": "h2",
    })

    results = list_active_events_by_type(conn, "REVIEW_DAILY")

    assert len(results) == 2
    assert results[0]["event_id"] == "evt_2"  # newest first
    assert results[1]["event_id"] == "evt_1"


def test_list_tickers_with_active_event_type_returns_distinct_sorted_tickers(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("INSERT INTO instrument VALUES ('us-nvda', 'NVDA', 'NASDAQ', 'Nvidia', '2026-07-18', NULL);")
    conn.execute("INSERT INTO instrument VALUES ('us-amd', 'AMD', 'NASDAQ', 'AMD', '2026-07-18', NULL);")
    conn.commit()
    # Two RESEARCH_IMPORT events for PLTR (must collapse to one ticker), one for NVDA,
    # and one SUPERSEDED-only AMD (must be excluded), plus a non-matching event_type for NVDA.
    insert_event(conn, {
        "event_id": "evt_pltr_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "RESEARCH_IMPORT", "effective_at": "2026-07-01", "ingested_at": "2026-07-01",
        "status": "ACTIVE", "title": "PLTR research 1", "body_markdown": "Body 1", "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_pltr_2", "event_sequence": 2, "instrument_id": "us-pltr",
        "event_type": "RESEARCH_IMPORT", "effective_at": "2026-07-10", "ingested_at": "2026-07-10",
        "status": "ACTIVE", "title": "PLTR research 2", "body_markdown": "Body 2", "content_hash": "h2",
    })
    insert_event(conn, {
        "event_id": "evt_nvda_1", "event_sequence": 3, "instrument_id": "us-nvda",
        "event_type": "RESEARCH_IMPORT", "effective_at": "2026-07-12", "ingested_at": "2026-07-12",
        "status": "ACTIVE", "title": "NVDA research", "body_markdown": "Body 3", "content_hash": "h3",
    })
    insert_event(conn, {
        "event_id": "evt_amd_superseded", "event_sequence": 4, "instrument_id": "us-amd",
        "event_type": "RESEARCH_IMPORT", "effective_at": "2026-07-05", "ingested_at": "2026-07-05",
        "status": "SUPERSEDED", "title": "AMD research (superseded)", "body_markdown": "Body 4",
        "content_hash": "h4",
    })
    insert_event(conn, {
        "event_id": "evt_nvda_other_type", "event_sequence": 5, "instrument_id": "us-nvda",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-13", "ingested_at": "2026-07-13",
        "status": "ACTIVE", "title": "NVDA news", "body_markdown": "Body 5", "content_hash": "h5",
    })

    result = list_tickers_with_active_event_type(conn, "RESEARCH_IMPORT")

    assert result == ["NVDA", "PLTR"]

