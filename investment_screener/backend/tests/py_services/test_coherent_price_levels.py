"""Pin coherent price levels: chart levels and valuation tiers merge into one numbered set in
SQLite, rewrites keep tier numbers, and the TradingView indicator draws only stored levels."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.price_level_repository import get_price_levels, replace_price_levels  # noqa: E402
from domain_model.projection_repository import add_projection_scenario, save_projection_version  # noqa: E402
import chart_levels  # noqa: E402
from update_price_levels import derive_and_write, derive_tiers_combined  # noqa: E402

PINE = REPO_ROOT / "plugins/tradingview/.apm/skills/operating-tradingview-charts/assets/pinescript-indicators/ai-ta-levels.pine"


def _bars():
    """Rise from 100 to 300, then fall to 190: a clean advance with a known retracement."""
    up = np.linspace(100, 300, 300)
    down = np.linspace(300, 190, 120)
    close = np.concatenate([up, down])
    idx = pd.bdate_range("2024-06-03", periods=len(close))
    vol = np.full(len(close), 1e6)
    vol[300 + 100:] = 5e6  # heavy volume near the end, around 190-200
    return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": vol}, index=idx)


def test_chart_levels_retrace_the_advance_that_made_the_high():
    c = chart_levels.compute_chart_levels(_bars())
    hi, lo = c["swingHigh"]["price"], c["swingLow"]["price"]
    bars = _bars()
    before_high = bars.loc[:bars["high"].idxmax()].tail(chart_levels.SWING_LOOKBACK_BARS)
    assert hi == round(300 * 1.01, 2) and lo == round(float(before_high["low"].min()), 2)
    assert c["fib"][0.618] == round(hi - (hi - lo) * 0.618, 2)
    assert c["shelves"] and all(s["low"] < s["high"] for s in c["shelves"])


def test_combined_buy_tiers_sit_below_price_and_fair_value_numbered_from_nearest():
    chart = chart_levels.compute_chart_levels(_bars())
    levels = derive_tiers_combined(bear_fv=60, base_fv=208, bull_fv=370, chart=chart,
                                   current_price=195, source_date="2026-10-22")
    active = [t for t in levels["buyTiers"] if t["status"] == "active"]
    assert [t["tier"] for t in active] == list(range(1, len(active) + 1))
    assert all(t["price"] < 195 and t["price"] <= 208 for t in active)
    assert [t["price"] for t in active] == sorted((t["price"] for t in active), reverse=True)
    assert any(t["source"].startswith("ta") or "+ta" in t["source"] for t in active)
    sells = levels["sellTiers"]
    assert [t["tier"] for t in sells] == list(range(1, len(sells) + 1)) and sells[0]["price"] >= 195
    assert sells[0]["price"] == 208 and sells[-1]["price"] == 370  # base fair value first, bull last
    # Bear-derived stop is >50% below price, so the stop comes from the support ladder instead.
    assert levels["stopLoss"]["status"] == "active" and levels["stopLoss"]["source"] == "ta"
    assert levels["stopLoss"]["price"] < active[-1]["price"]


def test_levels_within_two_percent_merge_into_one_tier():
    chart = {"asOf": "2026-10-22", "price": 195, "swingHigh": {"price": 300, "date": "2026-05-14"},
             "swingLow": {"price": 100, "date": "2025-05-06"}, "fib": {0.786: 157.0},
             "shelves": [], "ema50": 240.0, "ema200": 250.0}
    levels = derive_tiers_combined(bear_fv=60, base_fv=208, bull_fv=370, chart=chart,
                                   current_price=195, source_date="2026-10-22")
    active = [t for t in levels["buyTiers"] if t["status"] == "active"]
    # Fib 78.6% ($157) and DCF base x 0.75 ($156) are one tier; the nearer price is kept.
    assert len(active) == 1 and active[0]["price"] == 157.0
    assert "fibonacci 78.6%" in active[0]["basis"].lower() and "dcf" in active[0]["basis"].lower()
    assert active[0]["source"] == "ta+dcf"


def _seed(tmp_path, ticker="VRT", price=195.0):
    db = tmp_path / "t.sqlite"
    conn = initialize_db(str(db))
    inv = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
    save_projection_version(conn, inv, version=1, saved_at="2026-10-22T00:00:00Z", analyzed_at="2026-10-22T00:00:00Z",
                            model="m", fair_value=211.54, action="HOLD", rationale="r", snapshot_json="{}", source="AI_AGENT")
    for name, p in (("bear", 60.0), ("base", 208.0), ("bull", 370.0)):
        add_projection_scenario(conn, f"{inv}:1", name, weight=0.25, scenario_price=p)
    upsert_investment_price(conn, inv, price, "USD", "2026-10-22T15:00:00Z")
    conn.close()
    return db


def test_written_tiers_keep_their_numbers_and_survive_an_entry_price_rewrite(tmp_path, monkeypatch):
    db = _seed(tmp_path)
    chart = chart_levels.compute_chart_levels(_bars())
    derive_and_write("VRT", source="combined", db_path=db, chart=chart)
    import update_targets
    monkeypatch.setattr(update_targets, "DB_PATH", db)
    update_targets._save_entry_prices([{"ticker": "VRT", "targetEntryPrice": 184.0}])
    conn = initialize_db(str(db))
    levels = get_price_levels(conn, resolve_investment(conn, "VRT"))
    conn.close()
    buys = [t for t in levels["buy_tiers"] if t["status"] == "active"]
    assert [t["tier_number"] for t in buys] == list(range(1, len(buys) + 1))
    assert all(t["basis"] and t["source"] for t in buys)
    assert levels["target_entry"]["price"] == 184.0


def test_indicator_draws_only_stored_levels(tmp_path):
    from pine_level_inputs import fill_level_inputs, level_inputs
    db = _seed(tmp_path)
    derive_and_write("VRT", source="combined", db_path=db, chart=chart_levels.compute_chart_levels(_bars()))
    stored = level_inputs("VRT", db)
    assert stored["target_fair"] == 211.54 and "target_buy1" in stored and "target_trim1" in stored
    filled = fill_level_inputs(PINE.read_text(), "VRT", db)
    assert f'target_buy1    = input.float({stored["target_buy1"]:.2f}' in filled
    assert "target_buy3" in stored and f'target_buy3    = input.float({stored["target_buy3"]:.2f}' in filled
    src = PINE.read_text()
    for made_up in ("close * 0.90", "close * 0.85", "base_anchor * 1.15", "base_anchor * 1.30", "valid_buy * 0.92"):
        assert made_up not in src, f"indicator still invents a level: {made_up}"


def test_unlabelled_tiers_get_no_number_zero(tmp_path):
    db = _seed(tmp_path)
    conn = initialize_db(str(db))
    inv = resolve_investment(conn, "VRT")
    replace_price_levels(conn, inv, "1.0", "2026-10-22", "dcf", "",
                         [{"tier": 1, "price": 180.0, "basis": "b", "source": "dcf", "status": "active"}], [], None, None)
    levels = get_price_levels(conn, inv)
    conn.close()
    assert levels["buy_tiers"][0]["tier_number"] == 1


def test_tiny_fair_values_fall_back_to_dcf_levels_without_dividing_by_zero():
    """RGTI-style scenarios (bear and base $0, bull $0.67) must not crash the combined build."""
    chart = chart_levels.compute_chart_levels(_bars())
    levels = derive_tiers_combined(bear_fv=0.0, base_fv=0.0, bull_fv=0.67, chart=chart,
                                   current_price=11.6, source_date="2026-10-22")
    active = [t for t in levels["buyTiers"] + levels["sellTiers"] if t["status"] == "active"]
    assert levels["sellTiers"] and all(t["price"] > 0 for t in active)


def test_draw_sets_every_level_input_by_its_title(tmp_path, monkeypatch):
    """--draw sets the chart indicator's inputs from storage (0 for unstored levels), by input title."""
    import pine_level_inputs, pine_script_manager
    db = _seed(tmp_path)
    derive_and_write("VRT", source="combined", db_path=db, chart=chart_levels.compute_chart_levels(_bars()))
    calls = []
    monkeypatch.setattr(pine_script_manager, "tv_call", lambda *a: calls.append(a) or {"success": True, "study": "AI TA Levels v2"})
    out = pine_level_inputs.draw_levels("VRT", db)
    assert out["success"] and calls[0] == ("chart", "symbol", "VRT")
    import json as _json
    sent = _json.loads(calls[1][-1])
    titles = pine_level_inputs.input_titles()
    assert set(sent) == set(titles.values()) and len(titles) == 8
    stored = pine_level_inputs.level_inputs("VRT", db)
    assert sent[titles["target_buy1"]] == round(stored["target_buy1"], 2)
