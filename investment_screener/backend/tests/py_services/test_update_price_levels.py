#!/usr/bin/env python3
"""
test_update_price_levels.py — TDD test suite for update_price_levels.py

Tests cover:
  - DCF tier derivation formulas
  - Schema field completeness
  - Proximity flag computation
  - Atomic write to target-portfolio.json
  - Denormalized snapshot write to portfolio.json
  - Dry-run safety (no file modification)
  - Error handling for missing projections

Wave 1 Task 7B rewired `load_latest_projection` off `projections/{TICKER}.json`
onto `domain_model.sqlite` (ADR-029) — projection fixtures below seed a
`tmp_path`-backed SQLite database via `initialize_db` instead of writing a
projections directory, never touching the real `data/domain_model.sqlite` file.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# ── Import the module under test ────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.price_level_repository import get_price_levels  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    save_projection_version,
    add_projection_scenario,
)

from update_price_levels import (  # noqa: E402
    compute_proximity_flags,
    derive_and_write,
    derive_tiers_from_dcf,
    load_latest_projection,
)

# ── Constants used across tests ──────────────────────────────────────────────
BEAR_FV = 128.17
BASE_FV = 475.52
BULL_FV = 923.24
TODAY = datetime.now().strftime("%Y-%m-%d")

# Minimal valid projection entry
SAMPLE_PROJECTION = [
    {
        "ticker": "GOOG",
        "id": "d0d3da68-d15b-4ad6-a2da-8d6b06302e7e",
        "source": "AI_AGENT",
        "schemaVersion": "1.2",
        "version": 2,
        "savedAt": "2026-05-02T18:24:00Z",
        "updatedAt": "2026-05-02T18:58:24.050Z",
        "name": "AI Deep Dive — GOOG",
        "snapshot": {
            "price": 383.22,
            "currency": "USD",
            "shares": 12115000000,
            "revenue": 402836000000,
            "lastActualPS": 11.51,
        },
        "scenarios": {
            "bear": {"weight": 0.2, "scenarioPrice": BEAR_FV, "growthRate": 7, "netMargin": 24, "exitPE": 18, "qualityMultiplier": 0.95, "shareChange": -1.5},
            "base": {"weight": 0.55, "scenarioPrice": BASE_FV, "growthRate": 18, "netMargin": 33, "exitPE": 24, "qualityMultiplier": 1.12, "shareChange": -2.5},
            "bull": {"weight": 0.25, "scenarioPrice": BULL_FV, "growthRate": 22, "netMargin": 37, "exitPE": 32, "qualityMultiplier": 1.2, "shareChange": -3},
        },
        "aiThesis": {"model": "Claude", "rationale": "test", "fairValue": 517.98, "action": "BUY", "analyzedAt": "2026-05-02T18:24:00Z"},
        "globalSettings": {"discountRate": 10, "timeHorizon": 5},
        "dataPreferences": {"growthBasis": "next", "marginBasis": "ttm"},
    }
]

# Minimal valid target-portfolio.json
SAMPLE_TARGET = {
    "id": "target-portfolio",
    "name": "Target Portfolio",
    "schemaVersion": "1.0",
    "version": 1,
    "createdAt": "2026-01-01T00:00:00Z",
    "updatedAt": "2026-01-01T00:00:00Z",
    "description": "Test",
    "pillars": [{"id": "ai", "name": "AI Titans", "targetWeight": 100.0}],
    "holdings": [
        {
            "ticker": "GOOG",
            "name": "Alphabet",
            "pillarId": "ai",
            "targetWeight": 100.0,
            "role": "core",
        }
    ],
    "globalSettings": {
        "driftThresholdPct": 3.0,
        "criticalDriftPct": 5.0,
        "rebalanceFrequency": "quarterly",
    },
}

# Minimal valid portfolio.json
SAMPLE_PORTFOLIO = {
    "accounts": [
        {
            "name": "TFSA",
            "holdings": [
                {
                    "symbol": "GOOG",
                    "shares": 4,
                    "price": 383.22,
                    "market_value": 1532.88,
                    "book_price": 350.00,
                    "last_updated": "2026-06-21T00:00:00Z",
                }
            ],
        }
    ]
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_db(tmp_path: Path, ticker: str = "GOOG") -> Path:
    """Seed a tmp_path-backed SQLite DB with one AI_AGENT projection + bear/base/bull
    scenarios, mirroring SAMPLE_PROJECTION's shape."""
    entry = SAMPLE_PROJECTION[0]
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
        save_projection_version(
            conn, investment_id, version=entry["version"], saved_at=entry["savedAt"],
            analyzed_at=entry["aiThesis"]["analyzedAt"], model=entry["aiThesis"]["model"],
            fair_value=entry["aiThesis"]["fairValue"], action=entry["aiThesis"]["action"],
            rationale=entry["aiThesis"]["rationale"],
            snapshot_json=json.dumps(entry["snapshot"]), source="AI_AGENT",
        )
        projection_id = f"{investment_id}:{entry['version']}"
        for name, scen in entry["scenarios"].items():
            add_projection_scenario(
                conn, projection_id, name,
                weight=scen.get("weight"), growth_rate=scen.get("growthRate"),
                net_margin=scen.get("netMargin"), exit_pe=scen.get("exitPE"),
                quality_multiplier=scen.get("qualityMultiplier"),
                share_change=scen.get("shareChange"), scenario_price=scen.get("scenarioPrice"),
            )
    finally:
        conn.close()
    return db_path


def _make_target_json(tmp_path: Path) -> Path:
    target_path = tmp_path / "target-portfolio.json"
    target_path.write_text(json.dumps(SAMPLE_TARGET, indent=2))
    return target_path


def _make_portfolio_json(tmp_path: Path) -> Path:
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(SAMPLE_PORTFOLIO, indent=2))
    return portfolio_path


# ── Tests: derive_tiers_from_dcf ─────────────────────────────────────────────

class TestDeriveTiersFromDcf:
    def setup_method(self):
        self.tiers = derive_tiers_from_dcf(BEAR_FV, BASE_FV, BULL_FV, TODAY)

    def test_buy_tier_1_price(self):
        assert self.tiers["buyTiers"][0]["price"] == round(BASE_FV * 0.75, 2)

    def test_buy_tier_2_price(self):
        assert self.tiers["buyTiers"][1]["price"] == round(BEAR_FV * 1.05, 2)

    def test_sell_tier_1_price(self):
        assert self.tiers["sellTiers"][0]["price"] == round(BASE_FV, 2)

    def test_sell_tier_2_price(self):
        assert self.tiers["sellTiers"][1]["price"] == round(BULL_FV, 2)

    def test_sell_tier_3_price(self):
        assert self.tiers["sellTiers"][2]["price"] == round(BULL_FV * 1.20, 2)

    def test_stop_loss_price(self):
        assert self.tiers["stopLoss"]["price"] == round(BEAR_FV * 0.95, 2)

    def test_schema_version(self):
        assert self.tiers["schemaVersion"] == "1.0"

    def test_last_updated(self):
        assert self.tiers["lastUpdated"] == TODAY

    def test_last_updated_by(self):
        assert self.tiers["lastUpdatedBy"] == "dcf"

    def test_buy_tier_count(self):
        assert len(self.tiers["buyTiers"]) == 2

    def test_sell_tier_count(self):
        assert len(self.tiers["sellTiers"]) == 3


class TestDeriveTiersSchemaFields:
    def setup_method(self):
        self.tiers = derive_tiers_from_dcf(BEAR_FV, BASE_FV, BULL_FV, TODAY)

    def test_all_buy_tiers_active(self):
        for t in self.tiers["buyTiers"]:
            assert t["status"] == "active"

    def test_all_sell_tiers_active(self):
        for t in self.tiers["sellTiers"]:
            assert t["status"] == "active"

    def test_all_buy_tiers_source_dcf(self):
        for t in self.tiers["buyTiers"]:
            assert t["source"] == "dcf"

    def test_all_sell_tiers_source_dcf(self):
        for t in self.tiers["sellTiers"]:
            assert t["source"] == "dcf"

    def test_all_tiers_order_type_limit(self):
        for t in self.tiers["buyTiers"] + self.tiers["sellTiers"]:
            assert t["orderType"] == "limit"

    def test_buy_tier_actions(self):
        assert self.tiers["buyTiers"][0]["action"] == "accumulate"
        assert self.tiers["buyTiers"][1]["action"] == "accumulate_aggressive"

    def test_sell_tier_actions(self):
        assert self.tiers["sellTiers"][0]["action"] == "trim"
        assert self.tiers["sellTiers"][1]["action"] == "trim"
        assert self.tiers["sellTiers"][2]["action"] == "exit"

    def test_sell_trim_percentages(self):
        assert self.tiers["sellTiers"][0]["trimPct"] == 30
        assert self.tiers["sellTiers"][1]["trimPct"] == 50
        assert self.tiers["sellTiers"][2]["trimPct"] == 100

    def test_stop_loss_type(self):
        assert self.tiers["stopLoss"]["type"] == "thesis_breaker"

    def test_stop_loss_status(self):
        assert self.tiers["stopLoss"]["status"] == "active"

    def test_tier_numbers_sequential(self):
        for i, t in enumerate(self.tiers["buyTiers"], start=1):
            assert t["tier"] == i
        for i, t in enumerate(self.tiers["sellTiers"], start=1):
            assert t["tier"] == i


# ── Tests: compute_proximity_flags ───────────────────────────────────────────

class TestComputeProximityFlags:
    def setup_method(self):
        self.price_levels = derive_tiers_from_dcf(BEAR_FV, BASE_FV, BULL_FV, TODAY)
        # buyTier[1].price = round(BASE_FV * 0.75, 2) = 356.64
        # sellTier[1].price = 475.52
        # stopLoss.price = round(BEAR_FV * 0.95, 2) = 121.76

    def test_at_buy_tier_1(self):
        buy_tier_1_price = round(BASE_FV * 0.75, 2)
        # Price is exactly at buy tier (within 2%)
        flags = compute_proximity_flags(buy_tier_1_price, self.price_levels)
        assert "AT_BUY_TIER_1" in flags

    def test_at_buy_tier_1_slightly_below(self):
        buy_tier_1_price = round(BASE_FV * 0.75, 2)
        # Price is 1% below (within 2% of tier) — still triggers
        price = buy_tier_1_price * 0.99
        flags = compute_proximity_flags(price, self.price_levels)
        assert "AT_BUY_TIER_1" in flags

    def test_not_at_buy_tier_when_above(self):
        buy_tier_1_price = round(BASE_FV * 0.75, 2)
        # Price is above buy tier — not in the "approaching" zone
        price = buy_tier_1_price * 1.05
        flags = compute_proximity_flags(price, self.price_levels)
        assert "AT_BUY_TIER_1" not in flags

    def test_above_sell_tier_1(self):
        # Price well above sellTier[1]
        flags = compute_proximity_flags(BASE_FV * 1.10, self.price_levels)
        assert "ABOVE_SELL_TIER_1" in flags

    def test_at_sell_tier_1(self):
        sell_tier_1_price = round(BASE_FV, 2)
        # Price within 2% below sell tier
        price = sell_tier_1_price * 0.99
        flags = compute_proximity_flags(price, self.price_levels)
        assert "AT_SELL_TIER_1" in flags

    def test_at_stop_loss(self):
        stop_price = round(BEAR_FV * 0.95, 2)
        # Price within 3% above stop loss
        price = stop_price * 1.02
        flags = compute_proximity_flags(price, self.price_levels)
        assert "AT_STOP_LOSS" in flags

    def test_below_stop_loss(self):
        stop_price = round(BEAR_FV * 0.95, 2)
        # Price below stop loss
        flags = compute_proximity_flags(stop_price * 0.95, self.price_levels)
        assert "BELOW_STOP_LOSS" in flags

    def test_no_levels_when_none(self):
        flags = compute_proximity_flags(100.0, None)
        assert flags == ["NO_PRICE_LEVELS"]

    def test_no_levels_when_empty(self):
        flags = compute_proximity_flags(100.0, {})
        assert flags == ["NO_PRICE_LEVELS"]

    def test_no_flags_for_neutral_price(self):
        # A price well away from all tiers (between buy and sell, not near any)
        # BASE_FV * 0.75 ≈ 357, BASE_FV ≈ 476 — midpoint ~416 is neutral
        flags = compute_proximity_flags(416.0, self.price_levels)
        assert "AT_BUY_TIER_1" not in flags
        assert "AT_SELL_TIER_1" not in flags
        assert "ABOVE_SELL_TIER_1" not in flags
        assert "AT_STOP_LOSS" not in flags
        assert "BELOW_STOP_LOSS" not in flags


# ── Tests: load_latest_projection ────────────────────────────────────────────

class TestLoadLatestProjection:
    def test_loads_ai_agent_entry(self, tmp_path):
        db_path = _make_db(tmp_path)
        entry = load_latest_projection("GOOG", db_path=db_path)
        assert entry is not None
        assert entry["source"] == "AI_AGENT"

    def test_case_insensitive_ticker(self, tmp_path):
        db_path = _make_db(tmp_path)
        entry = load_latest_projection("goog", db_path=db_path)
        assert entry is not None

    def test_returns_none_for_missing_file(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        initialize_db(str(db_path)).close()
        entry = load_latest_projection("NVDA", db_path=db_path)
        assert entry is None

    def test_returns_none_for_empty_dir(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        initialize_db(str(db_path)).close()
        entry = load_latest_projection("GOOG", db_path=db_path)
        assert entry is None


# ── Tests: derive_and_write ───────────────────────────────────────────────────

class TestDeriveAndWrite:
    def test_write_price_levels_to_sqlite(self, tmp_path):
        """Wave 2 Task 9 producer cutover: priceLevels now persist via
        replace_price_levels() into domain_model.sqlite, not a rewrite of
        target-portfolio.json (which stays untouched by this write path until
        Task 10's consumer cutover)."""
        db_path = _make_db(tmp_path)
        target_path = _make_target_json(tmp_path)
        portfolio_path = _make_portfolio_json(tmp_path)
        original_target = target_path.read_text()

        result = derive_and_write(
            "GOOG",
            source="dcf",
            dry_run=False,
            target_json_path=target_path,
            portfolio_json_path=portfolio_path,
            db_path=db_path,
        )

        assert result["dry_run"] is False
        # target-portfolio.json is no longer rewritten by this producer.
        assert target_path.read_text() == original_target

        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "GOOG")
        stored = get_price_levels(conn, investment_id)
        conn.close()

        assert stored is not None
        assert stored["price_level_set"]["schema_version"] == "1.0"
        assert len(stored["buy_tiers"]) == 2
        assert len(stored["sell_tiers"]) == 3
        assert stored["stop_loss"] is not None

    def test_replace_preserves_existing_target_entry_price(self, tmp_path):
        """A pre-existing targetEntryPrice (a separate TARGET_ENTRY-kind row this
        script never sets) must survive a priceLevels replace, not be silently
        wiped by the full-object-rewrite semantics of replace_price_levels()."""
        from domain_model.price_level_repository import replace_price_levels

        db_path = _make_db(tmp_path)
        target_path = _make_target_json(tmp_path)
        portfolio_path = _make_portfolio_json(tmp_path)

        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "GOOG")
        replace_price_levels(
            conn, investment_id, schema_version="0.9", last_updated="2026-01-01",
            last_updated_by="manual", note=None, buy_tiers=[], sell_tiers=[],
            stop_loss=None, target_entry_price=250.0,
        )
        conn.close()

        derive_and_write(
            "GOOG", source="dcf", dry_run=False,
            target_json_path=target_path, portfolio_json_path=portfolio_path,
            db_path=db_path,
        )

        conn = initialize_db(str(db_path))
        stored = get_price_levels(conn, investment_id)
        conn.close()
        assert stored["target_entry"] is not None
        assert stored["target_entry"]["price"] == 250.0

    def test_write_snapshot_to_portfolio_json(self, tmp_path):
        db_path = _make_db(tmp_path)
        target_path = _make_target_json(tmp_path)
        portfolio_path = _make_portfolio_json(tmp_path)

        derive_and_write(
            "GOOG",
            source="dcf",
            dry_run=False,
            target_json_path=target_path,
            portfolio_json_path=portfolio_path,
            db_path=db_path,
        )

        written = json.loads(portfolio_path.read_text())
        # Find GOOG holding (may be in accounts[].holdings)
        all_holdings = []
        if "accounts" in written:
            for acct in written["accounts"]:
                all_holdings.extend(acct.get("holdings", []))
        elif "holdings" in written:
            all_holdings = written["holdings"]

        goog = next((h for h in all_holdings if h.get("symbol") == "GOOG"), None)
        assert goog is not None
        assert "priceLevelSnapshot" in goog
        snap = goog["priceLevelSnapshot"]
        assert "nextBuyTier" in snap
        assert "nextSellTier" in snap
        assert "proximityFlags" in snap

    def test_dry_run_does_not_write_target(self, tmp_path):
        db_path = _make_db(tmp_path)
        target_path = _make_target_json(tmp_path)
        portfolio_path = _make_portfolio_json(tmp_path)

        original_target = target_path.read_text()
        original_portfolio = portfolio_path.read_text()

        result = derive_and_write(
            "GOOG",
            source="dcf",
            dry_run=True,
            target_json_path=target_path,
            portfolio_json_path=portfolio_path,
            db_path=db_path,
        )

        assert result["dry_run"] is True
        assert target_path.read_text() == original_target
        assert portfolio_path.read_text() == original_portfolio

    def test_invalid_projection_raises(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        initialize_db(str(db_path)).close()
        target_path = _make_target_json(tmp_path)
        portfolio_path = _make_portfolio_json(tmp_path)

        with pytest.raises(ValueError, match="No projection found"):
            derive_and_write(
                "NVDA",
                source="dcf",
                dry_run=False,
                target_json_path=target_path,
                portfolio_json_path=portfolio_path,
                db_path=db_path,
            )

    def test_result_contains_price_levels(self, tmp_path):
        db_path = _make_db(tmp_path)
        target_path = _make_target_json(tmp_path)
        portfolio_path = _make_portfolio_json(tmp_path)

        result = derive_and_write(
            "GOOG",
            source="dcf",
            dry_run=True,
            target_json_path=target_path,
            portfolio_json_path=portfolio_path,
            db_path=db_path,
        )

        assert "price_levels" in result
        assert result["price_levels"]["schemaVersion"] == "1.0"

    def test_target_portfolio_json_untouched(self, tmp_path):
        """Since priceLevels now round-trips through domain_model.sqlite
        (Wave 2 Task 9), target-portfolio.json's updatedAt is no longer bumped
        by this producer — the JSON file is intentionally left as-is until
        Task 10's consumer cutover."""
        db_path = _make_db(tmp_path)
        target_path = _make_target_json(tmp_path)
        portfolio_path = _make_portfolio_json(tmp_path)

        derive_and_write(
            "GOOG",
            source="dcf",
            dry_run=False,
            target_json_path=target_path,
            portfolio_json_path=portfolio_path,
            db_path=db_path,
        )

        written = json.loads(target_path.read_text())
        assert written["updatedAt"] == "2026-01-01T00:00:00Z"

    def test_missing_portfolio_holding_does_not_crash(self, tmp_path):
        """derive_and_write should warn but not fail if ticker not in portfolio.json."""
        db_path = _make_db(tmp_path)
        target_path = _make_target_json(tmp_path)
        # Portfolio with no GOOG holding
        portfolio_path = tmp_path / "portfolio.json"
        portfolio_path.write_text(json.dumps({"accounts": [{"name": "TFSA", "holdings": []}]}))

        # Should not raise
        result = derive_and_write(
            "GOOG",
            source="dcf",
            dry_run=False,
            target_json_path=target_path,
            portfolio_json_path=portfolio_path,
            db_path=db_path,
        )
        assert result["ticker"] == "GOOG"
