#!/usr/bin/env python3
"""
test_update_price_levels.py — TDD test suite for update_price_levels.py

Tests cover:
  - DCF tier derivation formulas
  - Schema field completeness
  - Proximity flag computation
  - Persisting price levels and returning the snapshot computed from SQLite
  - Batch (--all) over the thesis holdings in SQLite
  - Dry-run safety (nothing stored)
  - Error handling for missing projections

Projection fixtures seed a `tmp_path`-backed SQLite database via `initialize_db`, never
touching the real `data/domain_model.sqlite` file.
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


def _seed_thesis_holding(db_path: Path, ticker: str, weight: float = 5.0) -> None:
    """Give an investment a target weight so it counts as a thesis holding."""
    from domain_model.investment_repository import update_investment_fields
    conn = initialize_db(str(db_path))
    update_investment_fields(conn, resolve_investment(conn, ticker), target_weight=weight)
    conn.close()


# ── Tests: derive_and_write ───────────────────────────────────────────────────

class TestDeriveAndWrite:
    def test_write_price_levels_to_sqlite(self, tmp_path):
        """priceLevels persist through replace_price_levels() into domain_model.sqlite."""
        db_path = _make_db(tmp_path)

        result = derive_and_write("GOOG", source="dcf", dry_run=False, db_path=db_path)

        assert result["dry_run"] is False
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
        """A pre-existing targetEntryPrice (a separate TARGET_ENTRY row this script never sets)
        survives a priceLevels replace."""
        from domain_model.price_level_repository import replace_price_levels

        db_path = _make_db(tmp_path)
        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "GOOG")
        replace_price_levels(
            conn, investment_id, schema_version="0.9", last_updated="2026-01-01",
            last_updated_by="manual", note=None, buy_tiers=[], sell_tiers=[],
            stop_loss=None, target_entry_price=250.0,
        )
        conn.close()

        derive_and_write("GOOG", source="dcf", dry_run=False, db_path=db_path)

        conn = initialize_db(str(db_path))
        stored = get_price_levels(conn, investment_id)
        conn.close()
        assert stored["target_entry"] is not None
        assert stored["target_entry"]["price"] == 250.0

    def test_returns_the_price_level_snapshot_computed_from_sqlite(self, tmp_path):
        """With a stored current price the result carries the next buy/sell tiers and proximity flags."""
        from domain_model.investment_price_repository import upsert_investment_price

        db_path = _make_db(tmp_path)
        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "GOOG")
        upsert_investment_price(conn, investment_id, price=383.22, currency="USD", fetched_at="2026-06-21T00:00:00Z")
        conn.close()

        result = derive_and_write("GOOG", source="dcf", dry_run=False, db_path=db_path)

        assert result["snapshot_written"] is True
        snap = result["price_level_snapshot"]
        assert snap is not None
        assert "nextBuyTier" in snap and "nextSellTier" in snap and "proximityFlags" in snap

    def test_dry_run_writes_nothing(self, tmp_path):
        """A dry run returns the derived levels and stores none."""
        db_path = _make_db(tmp_path)

        result = derive_and_write("GOOG", source="dcf", dry_run=True, db_path=db_path)

        assert result["dry_run"] is True
        conn = initialize_db(str(db_path))
        assert get_price_levels(conn, resolve_investment(conn, "GOOG")) is None
        conn.close()

    def test_invalid_projection_raises(self, tmp_path):
        """A ticker with no AI projection raises instead of writing anything."""
        db_path = tmp_path / "test.sqlite"
        initialize_db(str(db_path)).close()

        with pytest.raises(ValueError, match="No projection found"):
            derive_and_write("NVDA", source="dcf", dry_run=False, db_path=db_path)

    def test_result_contains_price_levels(self, tmp_path):
        """The result includes the derived priceLevels block."""
        result = derive_and_write("GOOG", source="dcf", dry_run=True, db_path=_make_db(tmp_path))

        assert "price_levels" in result
        assert result["price_levels"]["schemaVersion"] == "1.0"

    def test_retired_file_parameters_are_gone(self):
        """derive_and_write no longer takes the JSON path parameters and the module names no retired file."""
        import inspect
        import update_price_levels
        params = inspect.signature(derive_and_write).parameters
        assert "target_json_path" not in params and "portfolio_json_path" not in params
        assert not hasattr(update_price_levels, "TARGET_JSON") and not hasattr(update_price_levels, "PORTFOLIO_JSON")


# ── Tests: derive_and_write_all ───────────────────────────────────────────────

class TestDeriveAndWriteAll:
    def test_batch_writes_levels_for_every_thesis_holding_with_a_projection(self, tmp_path):
        """--all iterates the thesis holdings in SQLite, not a JSON file, and stores each one's levels."""
        from update_price_levels import derive_and_write_all
        db_path = _make_db(tmp_path)
        _seed_thesis_holding(db_path, "GOOG")

        out = derive_and_write_all(source="dcf", dry_run=False, db_path=db_path)

        assert [r["ticker"] for r in out["updated"]] == ["GOOG"] and out["skipped"] == [] and out["failed"] == []
        conn = initialize_db(str(db_path))
        assert get_price_levels(conn, resolve_investment(conn, "GOOG")) is not None
        conn.close()

    def test_holding_without_a_projection_is_reported_as_skipped_not_silently_dropped(self, tmp_path):
        """A thesis holding with no AI projection appears under 'skipped' with the reason."""
        from update_price_levels import derive_and_write_all
        db_path = _make_db(tmp_path)
        _seed_thesis_holding(db_path, "GOOG")
        _seed_thesis_holding(db_path, "NOPROJ")

        out = derive_and_write_all(source="dcf", dry_run=True, db_path=db_path)

        assert [r["ticker"] for r in out["updated"]] == ["GOOG"]
        assert [s["ticker"] for s in out["skipped"]] == ["NOPROJ"] and "No projection" in out["skipped"][0]["reason"]

    def test_empty_database_is_an_error_not_an_empty_result(self, tmp_path):
        """No thesis holdings at all raises; the old behaviour returned an empty list silently."""
        from update_price_levels import derive_and_write_all
        db_path = tmp_path / "empty.sqlite"
        initialize_db(str(db_path)).close()
        with pytest.raises(ValueError, match="thesis holdings"):
            derive_and_write_all(source="dcf", dry_run=True, db_path=db_path)

    def test_cli_all_exits_nonzero_when_nothing_to_do(self, tmp_path):
        """`--all` on a database with no thesis holdings exits 1 with a message."""
        import subprocess
        db_path = tmp_path / "empty.sqlite"
        initialize_db(str(db_path)).close()
        script = REPO_ROOT / "plugins/portfolio-advisor/scripts/update_price_levels.py"
        r = subprocess.run(["python3", str(script), "--all", "--db", str(db_path)], capture_output=True, text=True)
        assert r.returncode == 1 and "thesis holdings" in r.stderr


# ── Tests: bear-derived level sanity guard ───────────────────────────────────
# Real APLD numbers: v7 bear PV 3.62 wrote a $3.44 stop on a $26.25 stock;
# v8 bear PV 2.91 would write $2.76. A "thesis breaker" that far below price
# protects nothing, so it must be suppressed rather than emitted as active.

class TestBearLevelSanityGuard:
    def test_far_below_price_bear_levels_are_suppressed(self):
        tiers = derive_tiers_from_dcf(2.91, 21.78, 61.04, TODAY, current_price=26.25)
        assert tiers["stopLoss"]["status"] == "suppressed"
        assert tiers["buyTiers"][1]["status"] == "suppressed"
        assert ">50% below current price" in tiers["stopLoss"]["basis"]
        # base-derived buy tier and sell tiers stay active
        assert tiers["buyTiers"][0]["status"] == "active"
        assert all(t["status"] == "active" for t in tiers["sellTiers"])

    def test_bear_levels_near_price_stay_active(self):
        tiers = derive_tiers_from_dcf(22.0, 30.0, 45.0, TODAY, current_price=26.25)
        assert tiers["stopLoss"]["status"] == "active"
        assert tiers["buyTiers"][1]["status"] == "active"

    def test_without_current_price_behaviour_is_unchanged(self):
        tiers = derive_tiers_from_dcf(2.91, 21.78, 61.04, TODAY)
        assert tiers["stopLoss"]["status"] == "active"
        assert tiers["stopLoss"]["price"] == round(2.91 * 0.95, 2)

    def test_suppressed_stop_raises_no_proximity_flags(self):
        tiers = derive_tiers_from_dcf(2.91, 21.78, 61.04, TODAY, current_price=26.25)
        assert "BELOW_STOP_LOSS" not in compute_proximity_flags(1.0, tiers)

    def test_derive_and_write_uses_stored_current_price(self, tmp_path):
        from domain_model.investment_price_repository import upsert_investment_price
        db_path = _make_db(tmp_path)
        conn = initialize_db(str(db_path))
        bear = SAMPLE_PROJECTION[0]["scenarios"]["bear"]["scenarioPrice"]
        upsert_investment_price(conn, resolve_investment(conn, "GOOG"), bear * 3, "USD", TODAY)
        conn.close()
        derive_and_write("GOOG", source="dcf", dry_run=False, db_path=db_path)
        conn = initialize_db(str(db_path))
        stored = get_price_levels(conn, resolve_investment(conn, "GOOG"))
        conn.close()
        assert stored["stop_loss"]["status"] == "suppressed"
