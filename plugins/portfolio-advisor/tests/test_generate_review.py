"""Tests for generate_review.py's Wave 2 Task 10 rewire of compute_thesis_summary()
off target-portfolio.json's (buggy, always-empty) pillar.holdings read onto
domain_model.sqlite (investment.target_weight via list_investments).

Also documents the bug found & fixed during the rewire: the pre-rewire code
iterated ``thesis["pillars"][i]["holdings"]``, but target-portfolio.json's
pillar entries never have a "holdings" key — only the top-level
``thesis["holdings"]`` does — so EXIT/INITIATE counts were always 0.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)

import generate_review as gr  # noqa: E402


def _make_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        exit_id = resolve_investment(conn, "EXITME")
        update_investment_fields(conn, exit_id, target_weight=0.0)
        init_id = resolve_investment(conn, "NEWCO")
        update_investment_fields(conn, init_id, target_weight=5.0)
        held_id = resolve_investment(conn, "HELD")
        update_investment_fields(conn, held_id, target_weight=10.0)
    finally:
        conn.close()
    return db_path


def test_compute_thesis_summary_reads_target_weight_from_sqlite(tmp_path):
    db_path = _make_db(tmp_path)
    portfolio = [
        {"symbol": "EXITME", "shares": 10},
        {"symbol": "HELD", "shares": 5},
    ]
    thesis_meta = {"name": "Investment Thesis", "version": "9.8"}

    summary = gr.compute_thesis_summary(thesis_meta, portfolio, db_path=db_path)

    assert summary["exit_count"] == 1
    assert summary["exit_tickers"] == ["EXITME"]
    assert summary["initiate_count"] == 1
    assert summary["initiate_tickers"] == ["NEWCO"]
    assert summary["thesis_name"] == "Investment Thesis"
    assert summary["thesis_version"] == "9.8"


def test_compute_thesis_summary_missing_db_returns_empty(tmp_path):
    missing_db = tmp_path / "missing.sqlite"
    summary = gr.compute_thesis_summary({}, [], db_path=missing_db)
    assert summary["exit_count"] == 0
    assert summary["initiate_count"] == 0
