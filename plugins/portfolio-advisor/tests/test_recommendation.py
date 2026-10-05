"""Contract tests for the canonical recommendation function (recommendation.py).

Recommendations come from valuation + an explicit exit signal only. Target
weights play no part: the target is decided AFTER the recommendation.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recommendation import recommend, valuation_signal  # noqa: E402


class TestValuationSignal(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(valuation_signal(15.0), "BUY")
        self.assertEqual(valuation_signal(14.9), "HOLD")
        self.assertEqual(valuation_signal(-14.9), "HOLD")
        self.assertEqual(valuation_signal(-15.0), "SELL")
        self.assertIsNone(valuation_signal(None))


class TestRecommendHeld(unittest.TestCase):
    def test_overvalued_trims(self):
        r = recommend(held=True, upside_pct=-23.0)
        self.assertEqual(r["action"], "TRIM")
        self.assertEqual(r["valuation"], "SELL")

    def test_undervalued_accumulates(self):
        self.assertEqual(recommend(held=True, upside_pct=40.0)["action"], "ACCUMULATE")

    def test_fair_maintains(self):
        self.assertEqual(recommend(held=True, upside_pct=3.0)["action"], "MAINTAIN")

    def test_exit_signal_wins_over_valuation(self):
        self.assertEqual(recommend(held=True, upside_pct=80.0, exit_signal=True)["action"], "EXIT")

    def test_no_valuation_maintains(self):
        r = recommend(held=True, upside_pct=None)
        self.assertEqual(r["action"], "MAINTAIN")
        self.assertIn("no valuation", r["reason"].lower())


class TestRecommendNotHeld(unittest.TestCase):
    def test_buy_rated_initiates(self):
        self.assertEqual(recommend(held=False, upside_pct=30.0)["action"], "INITIATE")

    def test_otherwise_watchlist(self):
        self.assertEqual(recommend(held=False, upside_pct=-30.0)["action"], "WATCHLIST")
        self.assertEqual(recommend(held=False, upside_pct=5.0)["action"], "WATCHLIST")
        self.assertEqual(recommend(held=False, upside_pct=None)["action"], "WATCHLIST")

    def test_exit_signal_ignored_when_not_held(self):
        self.assertEqual(recommend(held=False, upside_pct=-30.0, exit_signal=True)["action"], "WATCHLIST")


class TestTargetsPlayNoPart(unittest.TestCase):
    def test_signature_has_no_target(self):
        import inspect
        params = inspect.signature(recommend).parameters
        self.assertFalse(any("target" in p for p in params))


if __name__ == "__main__":
    unittest.main()
