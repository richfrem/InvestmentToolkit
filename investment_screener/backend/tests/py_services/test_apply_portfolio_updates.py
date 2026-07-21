import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES_DIR))

import apply_portfolio_updates  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_investment_repository import list_account_investments  # noqa: E402

FIXTURE_PORTFOLIO = {
    "holdings": [{"symbol": "SNDK", "price": 1500.0, "last_updated": "2026-07-01T00:00:00.000Z"}],
    "tvSnapshot": {
        "snapshots": [
            {
                "accountType": "TFSA",
                "positions": [{"symbol": "SNDK", "quantity": 0.1, "avgFillPrice": 1000.0}],
            },
            {
                "accountType": "RRSP",
                "positions": [{"symbol": "SNDK", "quantity": 0.1, "avgFillPrice": 1000.0}],
            },
        ]
    },
}


def test_main_persists_patched_tfsa_rrsp_positions_to_sqlite(tmp_path, monkeypatch):
    """RED->GREEN: before Wave 3 Task 5.6's rewire, main() only wrote
    portfolio.json -- no account_investment rows existed for the patched
    SNDK quantities. This asserts the real per-account patched values (0.58
    TFSA / 0.36 RRSP, hardcoded in main()) land in domain_model.sqlite."""
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = tmp_path / "test.sqlite"

    monkeypatch.setattr(apply_portfolio_updates, "PORTFOLIO_PATH", portfolio_path)
    monkeypatch.setattr(apply_portfolio_updates, "DB_PATH", db_path)

    apply_portfolio_updates.main()

    conn = initialize_db(str(db_path))
    rows = {(r["account_id"], r["investment_id"]): r for r in list_account_investments(conn)}
    assert rows[("TFSA", "SNDK")]["quantity"] == 0.58
    assert rows[("TFSA", "SNDK")]["average_cost"] == 1483.9445
    assert rows[("RRSP", "SNDK")]["quantity"] == 0.36
    assert rows[("RRSP", "SNDK")]["average_cost"] == 1461.3306


def test_main_is_idempotent_no_duplicate_rows(tmp_path, monkeypatch):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = tmp_path / "test.sqlite"

    monkeypatch.setattr(apply_portfolio_updates, "PORTFOLIO_PATH", portfolio_path)
    monkeypatch.setattr(apply_portfolio_updates, "DB_PATH", db_path)

    apply_portfolio_updates.main()
    # Reset portfolio.json to fixture shape (main() rewrites holdings[]/tvSnapshot
    # positions in place) so a second run patches the same starting state again.
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    apply_portfolio_updates.main()

    conn = initialize_db(str(db_path))
    rows = list_account_investments(conn)
    sndk_rows = [r for r in rows if r["investment_id"] == "SNDK"]
    assert len(sndk_rows) == 2  # TFSA:SNDK, RRSP:SNDK -- no duplicates from re-run
