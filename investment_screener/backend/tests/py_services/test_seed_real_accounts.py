import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import list_accounts  # noqa: E402
from domain_model.seed_real_accounts import seed_real_accounts  # noqa: E402


def test_seed_creates_tfsa_rrsp_and_cash(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    seed_real_accounts(conn)
    accounts = {a["account_id"] for a in list_accounts(conn)}
    assert accounts == {"TFSA", "RRSP", "CASH"}


def test_seed_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    seed_real_accounts(conn)
    seed_real_accounts(conn)
    assert len(list_accounts(conn)) == 3
