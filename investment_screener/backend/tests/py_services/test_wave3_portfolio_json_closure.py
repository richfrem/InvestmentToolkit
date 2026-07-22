"""Wave 3 final closure — the last 4 real portfolio.json consumers now source
their data from domain_model.sqlite via portfolio_io.load_portfolio_state()
(ADR-030), not from the flat portfolio.json file.

Each test seeds a REAL temp SQLite domain model (no mocking of the aggregation
logic — CLAUDE.md rule 1) and points portfolio_io at it via its _DB_PATH, then
asserts the rewired consumer reads the computed total/weights from SQLite.
"""

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
PLUGIN_SCRIPTS = REPO_ROOT / "plugins/portfolio-advisor/scripts"
sys.path.insert(0, str(PY_SERVICES))
sys.path.insert(0, str(PLUGIN_SCRIPTS))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.exchange_rate_repository import upsert_exchange_rate  # noqa: E402


def _seed_db(path: Path, *, with_fx: bool = True) -> None:
    """TFSA: AAPL 10@150 (=1500), MSFT 5@200 (=1000). Portfolio total = 2500 USD."""
    conn = initialize_db(str(path))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    aapl = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    msft = resolve_investment(conn, "MSFT", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, aapl, price=150.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_investment_price(conn, msft, price=200.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_account_investment(conn, "TFSA", aapl, quantity=10, average_cost=140.0,
                              book_value=1400.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z")
    upsert_account_investment(conn, "TFSA", msft, quantity=5, average_cost=190.0,
                              book_value=950.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z")
    if with_fx:
        upsert_exchange_rate(conn, 1.40, "2026-07-20T00:00:00Z")
    conn.close()


@pytest.fixture
def db_backed(tmp_path, monkeypatch):
    """Seed a temp DB and repoint portfolio_io at it (never the real sqlite)."""
    db = tmp_path / "domain_model.sqlite"
    _seed_db(db)
    import portfolio_io
    importlib.reload(portfolio_io)
    monkeypatch.setattr(portfolio_io, "_DB_PATH", str(db))
    return db


def test_daily_brief_total_equity_from_sqlite(db_backed, monkeypatch):
    import daily_brief
    importlib.reload(daily_brief)
    # ensure daily_brief's function-local import binds to the patched portfolio_io
    assert daily_brief._load_total_equity() == pytest.approx(2500.0)


def test_relabel_actions_actual_pct_from_sqlite(db_backed):
    import relabel_actions
    importlib.reload(relabel_actions)
    pct = relabel_actions.build_actual_pct_map()
    assert pct["AAPL"] == pytest.approx(60.0)   # 1500/2500
    assert pct["MSFT"] == pytest.approx(40.0)   # 1000/2500


def test_ytd_current_balance_cad_is_usd_times_fx(db_backed):
    import ytd_return
    importlib.reload(ytd_return)
    # total_usd (2500) * exchange_rate (1.40) = 3500 CAD
    assert ytd_return.load_current_balance_cad() == pytest.approx(3500.0)


def test_ytd_current_balance_cad_falls_back_to_default_fx(tmp_path, monkeypatch):
    db = tmp_path / "domain_model.sqlite"
    _seed_db(db, with_fx=False)  # no broker_exchange_rate row → default 1.38
    import portfolio_io
    importlib.reload(portfolio_io)
    monkeypatch.setattr(portfolio_io, "_DB_PATH", str(db))
    import ytd_return
    importlib.reload(ytd_return)
    assert ytd_return.load_current_balance_cad() == pytest.approx(2500.0 * 1.38)


def test_generate_review_json_current_from_db(db_backed):
    import generate_review_json
    importlib.reload(generate_review_json)
    data = generate_review_json._compute_current_from_db()
    assert data["holdings"]["AAPL"] == pytest.approx(60.0)
    assert data["total_value"] == pytest.approx(2500.0)


def test_generate_grok_prompt_current_from_db(db_backed):
    import generate_grok_prompt
    importlib.reload(generate_grok_prompt)
    data = generate_grok_prompt._compute_current_from_db()
    assert data["holdings"]["MSFT"] == pytest.approx(40.0)
