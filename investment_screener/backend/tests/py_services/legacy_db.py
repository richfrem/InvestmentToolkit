"""Test helper: build a database file the way it looked BEFORE the migrator existed.

A realistic legacy file is the 0001 baseline minus the few columns that were added later
by the retired `SCHEMA_EVOLUTIONS` list, with no `schema_migrations` ledger. Tests use it
to prove `initialize_db()` adopts such a file without losing data.
"""

import sqlite3
from pathlib import Path

BASELINE = Path(__file__).resolve().parents[2] / "schema" / "domain_model" / "0001_baseline.sql"

LATE_COLUMNS = {
    "projection_version": ["source", "last_grok_sweep", "catalyst_updates_json"],
    "investment": ["sector", "industry", "last_deep_analysis_at"],
    "trade_log_entry": ["tv_order_id"],
}


def make_legacy_db(path: str, *, drop: dict[str, list[str]] | None = None) -> None:
    """Create `path` from the baseline, then drop `drop` columns (default: all late ones)."""
    conn = sqlite3.connect(path)
    conn.executescript(BASELINE.read_text())
    for table, columns in (LATE_COLUMNS if drop is None else drop).items():
        for column in columns:
            conn.execute(f'ALTER TABLE "{table}" DROP COLUMN {column};')
    conn.commit()
    conn.close()
