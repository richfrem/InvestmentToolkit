import json
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from portfolio_action import derive_action, _load_ai_upside

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))


class TestPortfolioAction(unittest.TestCase):
    def test_standard_rebalance_rules(self):
        self.assertEqual(derive_action("AAPL", 0, 0), "WATCHLIST")
        self.assertEqual(derive_action("AAPL", 0, 5), "INITIATE")
        self.assertEqual(derive_action("AAPL", 5, 5), "MAINTAIN")
        self.assertEqual(derive_action("AAPL", 2, 5), "ACCUMULATE") # Ratio 0.4 < 0.85
        self.assertEqual(derive_action("AAPL", 8, 5), "TRIM")       # Ratio 1.6 > 1.15

    def test_exit_rule_standard(self):
        # A normal stock not in thesis should be EXIT
        self.assertEqual(derive_action("NORMAL", 5, 0), "EXIT")

    def test_ai_conflict_override(self):
        # NBIS is a BUY with +186% upside. It should NOT return EXIT, it should return REVIEW.
        # We mock this by actually testing NBIS which has a projection file in the repo.
        action = derive_action("NBIS", 1.0, 0.0)
        self.assertEqual(action, "REVIEW", "NBIS has massive upside, it should override EXIT to REVIEW")

class TestLoadAiUpside(unittest.TestCase):
    """_load_ai_upside must read the domain_model SQLite DB (Wave 1 Task 7A),
    never projections/{TICKER}.json directly."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "domain_model.sqlite"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _seed(self, ticker, action, fair_value, price, source="AI_AGENT", version=1):
        from domain_model.db_client import initialize_db
        from domain_model.investment_repository import resolve_investment
        from domain_model.projection_repository import save_projection_version

        conn = initialize_db(str(self.db_path))
        investment_id = resolve_investment(conn, ticker)
        save_projection_version(
            conn, investment_id, version=version, saved_at="2026-07-01T00:00:00Z",
            action=action, fair_value=fair_value, source=source,
            snapshot_json=json.dumps({"price": price}),
        )
        conn.close()

    def test_computes_upside_for_buy_rated_projection(self):
        self._seed("NBIS", "BUY", fair_value=100.0, price=50.0)
        upside = _load_ai_upside("NBIS", self.db_path)
        self.assertAlmostEqual(upside, 100.0)

    def test_returns_none_for_maintain_rated_projection(self):
        self._seed("MSFT", "MAINTAIN", fair_value=100.0, price=90.0)
        self.assertIsNone(_load_ai_upside("MSFT", self.db_path))

    def test_returns_none_when_ticker_has_no_investment_row(self):
        self.assertIsNone(_load_ai_upside("NOPE", self.db_path))


if __name__ == '__main__':
    unittest.main()
