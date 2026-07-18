import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.instrument_repository import resolve_instrument  # noqa: E402


def test_resolve_instrument_creates_new_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    id_1 = resolve_instrument(conn, "PLTR", exchange="NASDAQ", name="Palantir Technologies")
    id_2 = resolve_instrument(conn, "PLTR", exchange="NASDAQ", name="Palantir Technologies")
    assert id_1 == id_2
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM instrument WHERE ticker = 'PLTR';")
    assert cursor.fetchone()[0] == 1
