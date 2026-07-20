"""Tests for verify_refresh.py's Wave 1 Task 7B rewire of `_load_ai_agent_upside`
(replacing two duplicated `projections/{TICKER}.json`-reading blocks) onto
domain_model.sqlite (ADR-029). All tests run against a `tmp_path`-backed SQLite
database via `initialize_db` — never the real `data/domain_model.sqlite` file.

verify_refresh.py is a pre-existing top-level script (not a library module) —
it runs its full consistency-check suite against the REAL portfolio/thesis
files at import time and ends with `sys.exit(0)`/`sys.exit(1)` depending on
whether that real data currently passes every check. That architecture
predates this rewire and is out of scope to restructure here. `sys.exit()`
raises `SystemExit` only as the module's very last statement — by that point
`_load_ai_agent_upside` (and every other module-level function/name) is
already fully defined — so the import below deliberately swallows `SystemExit`
and pulls the already-initialized module out of `sys.modules`, without
changing the script's own runtime behavior at all when run directly (`python3
verify_refresh.py` still exits 0/1 exactly as before).
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402

# Pre-existing, unrelated to this rewire: PortfolioAnalysis/ is gitignored
# (personal workspace artifacts) and may not exist in a fresh worktree, but
# the module reads REVIEWS_DIR.iterdir() at import time. Ensure it exists
# (empty is fine) so import doesn't crash with an unrelated FileNotFoundError.
(REPO_ROOT / "PortfolioAnalysis/strategic-reviews").mkdir(parents=True, exist_ok=True)

# Load via importlib (not a plain `import`) so the module object survives its
# own module-level `sys.exit(0)`/`sys.exit(1)` — a plain `import` would drop
# the partially-executed module from sys.modules when SystemExit propagates,
# but by the time sys.exit() runs (the script's last statement) every
# module-level name, including `_load_ai_agent_upside`, is already defined.
_spec = importlib.util.spec_from_file_location(
    "verify_refresh", REPO_ROOT / "plugins/portfolio-advisor/scripts/verify_refresh.py"
)
verify_refresh = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(verify_refresh)
except SystemExit:
    pass


def test_load_ai_agent_upside_returns_none_for_unknown_ticker(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    initialize_db(str(db_path)).close()
    monkeypatch.setattr(verify_refresh, "DB_PATH", db_path)

    assert verify_refresh._load_ai_agent_upside("ZZZZ") is None


def test_load_ai_agent_upside_returns_none_when_no_ai_agent_row(tmp_path, monkeypatch):
    """Original code filtered strictly by source == AI_AGENT with no fallback."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            fair_value=40.0, action="INITIATE", source="ETF_ANALYSIS",
        )
    finally:
        conn.close()
    monkeypatch.setattr(verify_refresh, "DB_PATH", db_path)

    assert verify_refresh._load_ai_agent_upside("DXYZ") is None


def test_load_ai_agent_upside_computes_negative_upside(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "CEG", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=100.0, action="SELL", source="AI_AGENT",
            snapshot_json='{"price": 200.0}',
        )
    finally:
        conn.close()
    monkeypatch.setattr(verify_refresh, "DB_PATH", db_path)

    upside = verify_refresh._load_ai_agent_upside("CEG")
    assert upside == -50.0


def test_load_holdings_map_reads_target_weight_and_rationale_from_sqlite(tmp_path):
    """Wave 2 Task 10 rewire: _load_holdings_map() reads target_weight and
    agent_rationale from investment via list_investments(), not
    target-portfolio.json's holdings array."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        aapl_id = resolve_investment(conn, "AAPL")
        from domain_model.investment_repository import update_investment_fields
        update_investment_fields(
            conn, aapl_id, target_weight=12.5, agent_rationale="Core holding."
        )
    finally:
        conn.close()

    holdings_map = verify_refresh._load_holdings_map(db_path)
    assert holdings_map["AAPL"] == {"targetWeight": 12.5, "agentRationale": "Core holding."}


def test_load_holdings_map_missing_db_returns_empty(tmp_path):
    missing_db = tmp_path / "missing.sqlite"
    assert verify_refresh._load_holdings_map(missing_db) == {}


def test_load_ai_agent_upside_none_when_missing_price_or_fv(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=None, action="HOLD", source="AI_AGENT",
        )
    finally:
        conn.close()
    monkeypatch.setattr(verify_refresh, "DB_PATH", db_path)

    assert verify_refresh._load_ai_agent_upside("NVDA") is None
