"""Purpose: verify news-sweep findings are recorded in the intelligence ledger, not in files.

Layer: Plugins / Portfolio Advisor / Tests.
Key Functions: parsing of ticker sections, idempotent recording, corrections, rejection of bad input.
Key Input Dependencies: record_news_sweep.py and a temporary ledger database (the real writer path).
"""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(ROOT / "investment_screener/backend/py_services"))

from record_news_sweep import parse_findings, record_findings  # noqa: E402

SWEEP = """# Daily sweep (ignored preamble)

## NVDA
- Board added $150B to the buyback authorization.
- Blackwell Ultra shipping to all hyperscalers.

## apld
- Polaris Forge 2 energized; lease signed with an investment-grade tenant.

## MACRO
- 10Y at 4.1%, VIX 14.9.

## Not a ticker heading because it has spaces
- ignored
"""


def _events(db: Path):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(
            "SELECT i.ticker, e.event_type, e.status, e.title, e.body_markdown, e.effective_at "
            "FROM intelligence_event e LEFT JOIN instrument i ON i.instrument_id = e.instrument_id "
            "ORDER BY e.event_sequence").fetchall()
    finally:
        conn.close()


def test_parse_reads_one_finding_per_ticker_section_and_a_macro_section():
    found = parse_findings(SWEEP)
    assert [t for t, _ in found] == ["NVDA", "APLD", None]
    assert "Blackwell Ultra" in found[0][1]
    assert found[2][1].startswith("- 10Y")


def test_parse_ignores_headings_that_are_not_tickers():
    assert parse_findings("## Not a ticker\n- x\n") == []
    assert parse_findings("no headings at all") == []


def test_record_writes_one_news_sweep_event_per_section(tmp_path):
    db = tmp_path / "intelligence.sqlite"
    receipt = record_findings(SWEEP, db, as_of="2026-10-10", source="grok")
    assert receipt == {"written": 3, "unchanged": 0, "corrected": 0, "tickers": ["NVDA", "APLD", "MACRO"]}
    rows = _events(db)
    assert [r[0] for r in rows] == ["NVDA", "APLD", None]
    assert {r[1] for r in rows} == {"NEWS_SWEEP"} and {r[2] for r in rows} == {"ACTIVE"}
    assert rows[0][3].startswith("grok sweep 2026-10-10: NVDA")
    assert "buyback" in rows[0][4]
    assert rows[0][5] == "2026-10-10"


def test_a_retry_changes_nothing_and_a_changed_finding_is_a_correction(tmp_path):
    db = tmp_path / "intelligence.sqlite"
    record_findings(SWEEP, db, as_of="2026-10-10", source="grok")
    again = record_findings(SWEEP, db, as_of="2026-10-10", source="grok")
    assert again["written"] == 0 and again["unchanged"] == 3
    assert len(_events(db)) == 3
    changed = SWEEP.replace("$150B", "$200B")
    third = record_findings(changed, db, as_of="2026-10-10", source="grok")
    assert third["corrected"] == 1 and third["unchanged"] == 2
    statuses = [r[2] for r in _events(db) if r[0] == "NVDA"]
    assert statuses == ["SUPERSEDED", "ACTIVE"]


def test_the_same_ticker_from_a_different_source_or_day_is_a_separate_event(tmp_path):
    db = tmp_path / "intelligence.sqlite"
    record_findings("## NVDA\n- a\n", db, as_of="2026-10-10", source="grok")
    record_findings("## NVDA\n- a\n", db, as_of="2026-10-10", source="claude")
    record_findings("## NVDA\n- a\n", db, as_of="2026-10-11", source="grok")
    assert len(_events(db)) == 3


def test_bad_input_is_rejected_before_the_database_exists(tmp_path):
    db = tmp_path / "intelligence.sqlite"
    with pytest.raises(ValueError):
        record_findings("", db, as_of="2026-10-10", source="grok")
    with pytest.raises(ValueError):
        record_findings("## NVDA\n- x\n", db, as_of="2026-13-40", source="grok")
    with pytest.raises(ValueError):
        record_findings("nothing parseable", db, as_of="2026-10-10", source="grok")
    with pytest.raises(ValueError):
        record_findings("## NVDA\n- x\n", db, as_of="2026-10-10", source="  ")
    assert not db.exists()
