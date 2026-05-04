import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from portfolio_action import derive_action

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

if __name__ == '__main__':
    unittest.main()
