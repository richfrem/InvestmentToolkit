import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    get_investment,
    update_investment_fields,
    list_investments,
)


def test_resolve_investment_creates_new_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    id_1 = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD", name="Apple Inc.")
    id_2 = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD", name="Apple Inc.")
    assert id_1 == id_2
    cursor = conn.execute("SELECT COUNT(*) FROM investment WHERE symbol = 'AAPL';")
    assert cursor.fetchone()[0] == 1


def test_resolve_investment_supports_cash_concepts(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
    row = get_investment(conn, investment_id)
    assert row["asset_class"] == "CASH"
    assert row["symbol"] == "CASH_USD"


def test_get_investment_returns_none_for_unknown_id(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_investment(conn, "does-not-exist") is None


def test_update_investment_fields_updates_only_specified_fields(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    update_investment_fields(
        conn, investment_id,
        lifecycle_status="active", target_weight=0.05, target_action="ACCUMULATE",
    )
    row = get_investment(conn, investment_id)
    assert row["lifecycle_status"] == "active"
    assert row["target_weight"] == 0.05
    assert row["target_action"] == "ACCUMULATE"
    assert row["symbol"] == "AAPL"


def test_update_investment_fields_preserves_standing_decision_on_partial_update(tmp_path):
    """The standingDecision anchor rule (CLAUDE.md #8) must never be silently
    clobbered by an update call that doesn't intend to touch it -- this is the
    single highest-risk item in this wave.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "PLTR", asset_class="EQUITY", currency="USD")
    update_investment_fields(
        conn, investment_id,
        standing_decision_type="HOLD",
        standing_decision_reason="DCF delta <15%, anchor holds",
        standing_decision_source="daily_brief.py",
    )
    update_investment_fields(conn, investment_id, target_weight=0.03)
    row = get_investment(conn, investment_id)
    assert row["standing_decision_type"] == "HOLD"
    assert row["standing_decision_reason"] == "DCF delta <15%, anchor holds"
    assert row["target_weight"] == 0.03


def test_update_investment_fields_rejects_unknown_field(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "MSFT", asset_class="EQUITY", currency="USD")
    try:
        update_investment_fields(conn, investment_id, not_a_real_column="oops")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "not_a_real_column" in str(exc)


def test_list_investments_filters_by_watchlist_flag(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    a = resolve_investment(conn, "DRAM", asset_class="EQUITY", currency="USD")
    resolve_investment(conn, "MSFT", asset_class="EQUITY", currency="USD")
    update_investment_fields(conn, a, is_watchlisted=True)
    watchlisted = list_investments(conn, is_watchlisted=True)
    assert {r["investment_id"] for r in watchlisted} == {a}
