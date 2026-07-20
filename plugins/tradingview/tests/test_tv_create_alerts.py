#!/usr/bin/env python3
"""Tests for tv_create_alerts.py's Wave 2 Task 10 rewire off the (now archived)
projections/{TICKER}.json and target-portfolio.json reads onto domain_model.sqlite.

Bug found & fixed during the rewire: projections/ was archived at the end of
Wave 1 (commit 730daddb), so load_latest_ai_entry()/get_all_tickers() had been
silently returning None/[] for every ticker ever since — this rewire restores
real functionality.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    save_projection_version,
    add_projection_scenario,
)
from domain_model.price_level_repository import replace_price_levels  # noqa: E402

import tv_create_alerts  # noqa: E402


class TestLoadLatestAiEntry(unittest.TestCase):
    def test_returns_none_for_unknown_ticker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            initialize_db(str(db_path)).close()
            self.assertIsNone(tv_create_alerts.load_latest_ai_entry("ZZZZ", db_path))

    def test_returns_entry_with_scenarios_and_fair_value(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            conn = initialize_db(str(db_path))
            try:
                investment_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
                projection_id = save_projection_version(
                    conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
                    fair_value=200.0, action="BUY", source="AI_AGENT",
                )
                add_projection_scenario(conn, projection_id, "bear", scenario_price=150.0)
                add_projection_scenario(conn, projection_id, "base", scenario_price=200.0)
                add_projection_scenario(conn, projection_id, "bull", scenario_price=250.0)
            finally:
                conn.close()

            entry = tv_create_alerts.load_latest_ai_entry("NVDA", db_path)
            self.assertIsNotNone(entry)
            self.assertEqual(entry["aiThesis"]["fairValue"], 200.0)
            self.assertEqual(entry["scenarios"]["bear"]["scenarioPrice"], 150.0)
            self.assertEqual(entry["scenarios"]["bull"]["scenarioPrice"], 250.0)

            levels = tv_create_alerts.get_alert_levels(entry)
            prices = sorted(p for _, p in levels)
            self.assertEqual(prices, [150.0, 200.0, 200.0, 250.0])


class TestGetTierAlertLevels(unittest.TestCase):
    def test_reads_price_levels_from_sqlite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            conn = initialize_db(str(db_path))
            try:
                investment_id = resolve_investment(conn, "SNDK", asset_class="EQUITY")
                replace_price_levels(
                    conn, investment_id,
                    schema_version="1", last_updated="2026-07-01", last_updated_by="test",
                    note=None,
                    buy_tiers=[{"tier": 1, "price": 100.0, "status": "active"}],
                    sell_tiers=[{"tier": 1, "price": 150.0, "trimPct": 30, "status": "active"}],
                    stop_loss={"price": 80.0, "status": "active"},
                    target_entry_price=None,
                )
            finally:
                conn.close()

            levels = tv_create_alerts.get_tier_alert_levels("SNDK", db_path)
            prices = sorted(p for _, p in levels)
            self.assertEqual(prices, [80.0, 100.0, 150.0])

    def test_returns_empty_for_unknown_ticker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            initialize_db(str(db_path)).close()
            self.assertEqual(tv_create_alerts.get_tier_alert_levels("ZZZZ", db_path), [])


class TestGetAllTickers(unittest.TestCase):
    def test_lists_symbols_with_projections(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            conn = initialize_db(str(db_path))
            try:
                investment_id = resolve_investment(conn, "AMD", asset_class="EQUITY")
                save_projection_version(
                    conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
                    fair_value=100.0, action="HOLD", source="AI_AGENT",
                )
            finally:
                conn.close()

            tickers = tv_create_alerts.get_all_tickers(db_path)
            self.assertEqual(tickers, ["AMD"])


if __name__ == "__main__":
    unittest.main()
