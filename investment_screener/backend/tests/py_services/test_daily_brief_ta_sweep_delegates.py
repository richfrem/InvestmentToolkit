"""Guards against daily_brief.py re-implementing ta_sweep_batch.py's save_sweep_results()
write. TA_SWEEP_PATH must only ever be written by ta_sweep_batch.py's own save logic —
daily_brief.py may read it back in, but must not open it in write mode itself.
"""
import ast
from pathlib import Path


def test_daily_brief_does_not_write_ta_sweep_path_directly():
    source = Path("plugins/portfolio-advisor/scripts/daily_brief.py").read_text()
    tree = ast.parse(source)
    # daily_brief.py must never open TA_SWEEP_PATH itself in write mode — only
    # ta_sweep_batch.py's save_sweep_results() is allowed to write that file.
    # (Other json.dump calls, e.g. for the daily brief's own snapshot file, are unrelated
    # and must remain untouched — this check is scoped to TA_SWEEP_PATH specifically.)
    write_opens_on_ta_sweep_path = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "TA_SWEEP_PATH"
        and len(node.args) > 1
        and isinstance(node.args[1], ast.Constant)
        and "w" in str(node.args[1].value)
    ]
    assert len(write_opens_on_ta_sweep_path) == 0, "daily_brief.py must not open TA_SWEEP_PATH for writing — only ta_sweep_batch.py's save_sweep_results() should write it"


def test_ta_age_hours_reads_from_database(tmp_path):
    """_ta_age_hours must read age of TECHNICAL_SWEEP from SQLite database."""
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[4]
    py_services = repo_root / "investment_screener/backend/py_services"
    sys.path.insert(0, str(py_services))
    sys.path.insert(0, str(repo_root / "plugins/portfolio-advisor/scripts"))
    
    from daily_brief import _ta_age_hours  # noqa: PLC0415
    from intelligence.db_client import initialize_db  # noqa: E402
    from intelligence.event_store import append_event  # noqa: E402

    import sqlite3
    import time

    db_path = tmp_path / "intelligence.sqlite"
    jsonl_path = tmp_path / "observations.jsonl"

    # Initialize test database
    conn = initialize_db(str(db_path))
    conn.execute("INSERT INTO instrument VALUES ('us-msft', 'MSFT', 'NASDAQ', 'Microsoft', '2026-07-18', NULL);")
    conn.commit()
    conn.close()

    # Append TECHNICAL_SWEEP to ledger
    append_event(
        str(jsonl_path),
        event_type="TECHNICAL_SWEEP",
        effective_at="2026-07-18",
        status="ACTIVE",
        title="TA Sweep MSFT",
        body_markdown="Sweep for MSFT",
        ticker="MSFT",
        source_id="tradingview-cdp",
        payload={"ticker": "MSFT"},
        idempotency_key="ta-sweep-msft-2026-07-18"
    )

    # Replay event to DB
    from intelligence.replay_ledger import replay_events_to_db
    conn = sqlite3.connect(str(db_path))
    replay_events_to_db(str(jsonl_path), conn)
    conn.close()

    age = _ta_age_hours(db_path=str(db_path))
    assert age is not None
    # Since it was scanned just now (ingested_at is now), the age should be very small (< 0.1 hours)
    assert age >= 0
    assert age < 1.0

