import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from portfolio_action import derive_action  # noqa: E402
from recommendation import recommend, recommend_all  # noqa: E402


# Source-data and override resistance are exercised with real seeded SQLite in
# test_canonical_recommendation_consumers.py, including missing-ticker behavior.


class TestRecommendAllReadsSqlite(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "domain_model.sqlite"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _seed(self, ticker, action, fair_value, price):
        from domain_model.db_client import initialize_db
        from domain_model.investment_repository import resolve_investment
        from domain_model.projection_repository import save_projection_version

        conn = initialize_db(str(self.db_path))
        investment_id = resolve_investment(conn, ticker)
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            action=action, fair_value=fair_value, source="AI_AGENT",
            snapshot_json=json.dumps({"price": price}),
        )
        conn.close()

    def test_unheld_buy_rated_is_initiate_with_upside(self):
        self._seed("NBIS", "BUY", fair_value=100.0, price=50.0)
        rec = recommend_all(str(self.db_path))["NBIS"]
        self.assertEqual(rec["action"], "INITIATE")
        self.assertAlmostEqual(rec["upside_pct"], 100.0)
        self.assertFalse(rec["held"])

    def test_unheld_overvalued_is_watchlist(self):
        self._seed("MSFT", "SELL", fair_value=50.0, price=100.0)
        self.assertEqual(recommend_all(str(self.db_path))["MSFT"]["action"], "WATCHLIST")


if __name__ == "__main__":
    unittest.main()
