import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.pillar_repository import (  # noqa: E402
    resolve_pillar,
    resolve_sub_strategy,
    list_pillars,
    list_sub_strategies,
)


def test_resolve_pillar_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    id_1 = resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.35)
    id_2 = resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.35)
    assert id_1 == id_2 == "AI_INFRA"
    rows = list_pillars(conn)
    assert len(rows) == 1
    assert rows[0]["target_weight"] == 0.35


def test_resolve_sub_strategy_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    resolve_pillar(conn, "AI_INFRA", "AI Infrastructure")
    id_1 = resolve_sub_strategy(conn, "AI_COMPUTE", "AI_INFRA", "AI Compute")
    id_2 = resolve_sub_strategy(conn, "AI_COMPUTE", "AI_INFRA", "AI Compute")
    assert id_1 == id_2 == "AI_COMPUTE"
    rows = list_sub_strategies(conn, pillar_id="AI_INFRA")
    assert len(rows) == 1


def test_resolve_pillar_updates_on_repeat_call_with_new_weight(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.30)
    resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.35)
    rows = list_pillars(conn)
    assert rows[0]["target_weight"] == 0.35
